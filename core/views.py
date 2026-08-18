from datetime import date, timedelta

from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import User, Customer, Plan, Sale, CashCount, Outflow
from .serializers import (
    UserSerializer, UserWriteSerializer, PlanSerializer,
    PlanPublicSerializer, CustomerSerializer, SaleSerializer,
    SaleCreateSerializer, CashCountSerializer, OutflowSerializer,
)
from .reports import build_sales_pdf, build_sales_xlsx, build_cash_pdf


def _user_payload(user):
    return {'id': user.id, 'name': user.name, 'email': user.email,
            'role': user.role, 'active': user.active}


class IsAdminMixin:
    def check_admin(self, request):
        user = request.user
        if not user or not getattr(user, 'active', True) or user.role != 'admin':
            return Response({'error': 'Se requieren permisos de administrador'},
                            status=status.HTTP_403_FORBIDDEN)
        return None


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cursor.fetchall()]
            user_count = User.objects.count()
            plan_count = Plan.objects.count()
            return Response({
                'status': 'ok',
                'tables': tables,
                'users': user_count,
                'plans': plan_count,
                'db': str(connection.settings_dict['NAME']),
            })
        except Exception as e:
            return Response({'status': 'error', 'detail': str(e)}, status=500)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """Login del frontend: envía solo {password}. También acepta
        {email, password}. Las credenciales son datos mock."""
        email = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password') or ''

        if not password:
            return Response({'error': 'Contraseña requerida'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = None
        if email:
            user = User.objects.filter(email__iexact=email, active=True).first()
            if user and not user.check_password(password):
                user = None
        else:
            for candidate in User.objects.filter(active=True):
                if candidate.check_password(password):
                    user = candidate
                    break

        if user is None:
            return Response({'error': 'Credenciales inválidas'},
                            status=status.HTTP_401_UNAUTHORIZED)

        token = RefreshToken.for_user(user)
        return Response({'token': str(token.access_token), 'user': _user_payload(user)})


class MeView(APIView):
    def get(self, request):
        return Response({'user': _user_payload(request.user)})


class PlanListView(IsAdminMixin, APIView):
    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        return Response(PlanSerializer(Plan.objects.all().order_by('type', 'code'), many=True).data)

    def post(self, request):
        error = self.check_admin(request)
        if error:
            return error
        serializer = PlanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PlanDetailView(IsAdminMixin, APIView):
    def _get_plan(self, pk):
        try:
            return Plan.objects.get(id=pk)
        except Plan.DoesNotExist:
            return None

    def put(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        plan = self._get_plan(pk)
        if not plan:
            return Response({'error': 'Plan no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        serializer = PlanSerializer(plan, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)


class ActivePlansView(APIView):
    def get(self, request):
        plans = Plan.objects.filter(active=True).order_by('type', 'code')
        return Response(PlanPublicSerializer(plans, many=True).data)


class CustomerListView(APIView):
    """Busqueda de clientes por kardex o nombre (para autocompletar)."""
    def get(self, request):
        q = request.query_params.get('q', '').strip()
        qs = Customer.objects.all().order_by('code')
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
        return Response(CustomerSerializer(qs[:20], many=True).data)


class SaleListView(APIView):
    def get(self, request):
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        rtype = request.query_params.get('requestType')
        qs = Sale.objects.select_related('plan', 'createdBy').all()
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)
        if rtype:
            qs = qs.filter(requestType=rtype)
        return Response(SaleSerializer(qs, many=True).data)

    def post(self, request):
        serializer = SaleCreateSerializer(data=request.data, context={'user': request.user})
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)
        sale = serializer.save()
        return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)


class SaleDetailView(IsAdminMixin, APIView):
    def put(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        try:
            sale = Sale.objects.get(id=pk)
        except Sale.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        plan = sale.plan
        if data.get('planId'):
            plan = Plan.objects.filter(id=data['planId'], active=True).first()
            if not plan:
                return Response({'error': 'Plan no encontrado o inactivo'},
                                status=status.HTTP_400_BAD_REQUEST)
            if plan.type != data.get('serviceType', sale.serviceType):
                return Response({'error': 'El plan no pertenece al tipo de servicio'},
                                status=status.HTTP_400_BAD_REQUEST)

        sale.date = data.get('date', sale.date)
        sale.clientCode = data.get('clientCode', sale.clientCode)
        sale.clientName = data.get('clientName', sale.clientName)
        sale.serviceType = data.get('serviceType', sale.serviceType)
        sale.requestType = data.get('requestType', sale.requestType)
        sale.plan = plan
        sale.total = plan.total
        sale.lastEditedBy = request.user
        sale.lastEditedAt = timezone.now()
        sale.save()
        return Response(SaleSerializer(sale).data)


class UserListView(IsAdminMixin, APIView):
    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        return Response(UserSerializer(User.objects.all().order_by('id'), many=True).data)

    def post(self, request):
        error = self.check_admin(request)
        if error:
            return error
        serializer = UserWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)
        if not request.data.get('password'):
            return Response({'error': 'La contraseña es requerida'},
                            status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(IsAdminMixin, APIView):
    def put(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        serializer = UserWriteSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(UserSerializer(user).data)


class CashCountView(APIView):
    def get(self, request):
        try:
            d = request.query_params.get('date') or date.today().isoformat()
            cash_count = CashCount.objects.filter(date=d).first()
            outflows = list(Outflow.objects.filter(date=d).values('id', 'date', 'personName', 'amount', 'concept', 'created_at'))
            cc_data = None
            if cash_count:
                cc_data = {
                    'id': cash_count.id,
                    'date': str(cash_count.date),
                    'coin_050': cash_count.coin_050,
                    'coin_1': cash_count.coin_1,
                    'coin_2': cash_count.coin_2,
                    'coin_5': cash_count.coin_5,
                    'bill_10': cash_count.bill_10,
                    'bill_20': cash_count.bill_20,
                    'bill_50': cash_count.bill_50,
                    'bill_100': cash_count.bill_100,
                    'bill_200': cash_count.bill_200,
                }
            total_out = Outflow.objects.filter(date=d).aggregate(s=Sum('amount'))['s'] or 0
            return Response({
                'cashCount': cc_data,
                'outflows': outflows,
                'totalOutflows': float(total_out),
            })
        except Exception as e:
            import traceback
            return Response({'error': str(e), 'trace': traceback.format_exc()}, status=500)

    def post(self, request):
        data = request.data
        d = data.get('date') or date.today().isoformat()
        fields = ['coin_050', 'coin_1', 'coin_2', 'coin_5',
                  'bill_10', 'bill_20', 'bill_50', 'bill_100', 'bill_200']
        payload = {f: max(0, int(data.get(f, 0) or 0)) for f in fields}
        cash_count, _ = CashCount.objects.update_or_create(
            date=d, defaults={**payload, 'createdBy': request.user})
        return Response(CashCountSerializer(cash_count).data)


class OutflowCreateView(APIView):
    def post(self, request):
        data = request.data
        d = data.get('date') or date.today().isoformat()
        person_name = (data.get('personName') or '').strip()
        amount = data.get('amount')
        if not person_name:
            return Response({'error': 'Nombre requerido'}, status=status.HTTP_400_BAD_REQUEST)
        if amount is None:
            return Response({'error': 'Monto requerido'}, status=status.HTTP_400_BAD_REQUEST)
        outflow = Outflow.objects.create(
            date=d, personName=person_name,
            amount=float(amount),
            concept=data.get('concept', ''),
            createdBy=request.user,
        )
        return Response({
            'outflow': OutflowSerializer(outflow).data,
            'totalOutflows': _total_outflows(d),
        }, status=status.HTTP_201_CREATED)


class OutflowDetailView(APIView):
    def delete(self, request, pk):
        try:
            outflow = Outflow.objects.get(id=pk)
        except Outflow.DoesNotExist:
            return Response({'error': 'Salida no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        d = outflow.date
        outflow.delete()
        return Response({'totalOutflows': _total_outflows(d)})


def _total_outflows(d):
    return Outflow.objects.filter(date=d).aggregate(s=Sum('amount'))['s'] or 0


def _first_error(serializer):
    errors = serializer.errors
    if isinstance(errors, dict):
        for key, value in errors.items():
            if isinstance(value, list) and value:
                return str(value[0])
            return str(value)
    return 'Error de validación'
