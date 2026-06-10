from __future__ import annotations

from django.http import HttpRequest
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from users.authentication import DocuparseAuthentication
from users.serializers import LoginSerializer, UserMeSerializer


@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def login_view(request: Request) -> Response:
    from django.contrib.auth import get_user_model

    email = request.data.get("email", "")
    password = request.data.get("password", "")

    # Check if account exists but is inactive before authenticate() swallows it
    User = get_user_model()
    try:
        db_user = User.objects.get(username=email)
        if not db_user.is_active:
            return Response(
                {"detail": "Conta inativa. Aguarde ativação pelo administrador."},
                status=status.HTTP_403_FORBIDDEN,
            )
    except User.DoesNotExist:
        pass

    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"detail": "Credenciais inválidas."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user = serializer.validated_data["user"]
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserMeSerializer(user).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def logout_view(request: Request) -> Response:
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response(
            {"detail": "Token inválido ou já expirado."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError:
        return Response(
            {"detail": "Token inválido ou já expirado."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(status=status.HTTP_204_NO_CONTENT)


# Re-use SimpleJWT's built-in refresh view
refresh_view = TokenRefreshView.as_view()


@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def register_view(request: Request) -> Response:
    from users.serializers import RegisterSerializer
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    data = serializer.validated_data
    user = User.objects.create_user(
        username=data["email"],
        email=data["email"],
        password=data["password"],
        first_name=data["name"],
        is_active=False,
    )
    from documents.models import Tenant, UserProfile
    tenant = Tenant.objects.first()
    if tenant:
        UserProfile.objects.create(user=user, tenant=tenant, role_ref=None)

    return Response(
        {
            "id": user.pk,
            "email": user.email,
            "name": user.first_name,
            "is_active": False,
            "message": "Conta criada. Aguarde ativação pelo administrador.",
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@authentication_classes([DocuparseAuthentication])
@permission_classes([IsAuthenticated])
def me_view(request: Request) -> Response:
    return Response(UserMeSerializer(request.user).data)
