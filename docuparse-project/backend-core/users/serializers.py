from __future__ import annotations

from typing import Any

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from users.models import Role


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        email: str = data["email"]
        password: str = data["password"]

        user = authenticate(username=email, password=password)
        if user is None:
            # Distinguish "inactive account" from "wrong credentials"
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                db_user = User.objects.get(username=email)
                if not db_user.is_active:
                    raise serializers.ValidationError(
                        {"detail": "Conta inativa. Aguarde ativação pelo administrador."},
                        code="inactive",
                    )
            except User.DoesNotExist:
                pass
            raise serializers.ValidationError(
                {"detail": "Credenciais inválidas."},
                code="invalid_credentials",
            )

        data["user"] = user
        return data


class _RoleSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class UserMeSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="pk")
    name = serializers.SerializerMethodField()
    email = serializers.EmailField()
    is_active = serializers.BooleanField()
    role = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    def get_name(self, obj: Any) -> str:
        return obj.get_full_name() or obj.first_name or obj.username

    def get_role(self, obj: Any) -> dict | None:
        profile = getattr(obj, "docuparse_profile", None)
        if not profile or not profile.role_ref:
            return None
        return {"id": str(profile.role_ref.id), "name": profile.role_ref.name}

    def get_permissions(self, obj: Any) -> list[str]:
        profile = getattr(obj, "docuparse_profile", None)
        if not profile or not profile.role_ref:
            return []
        return list(
            profile.role_ref.permissions.values_list("code", flat=True)
        )


# ─── User Management Serializers ─────────────────────────────────────────────

class UserListSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="pk")
    name = serializers.SerializerMethodField()
    email = serializers.EmailField()
    is_active = serializers.BooleanField()
    role = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField()

    def get_name(self, obj: Any) -> str:
        return obj.get_full_name() or obj.first_name or obj.username

    def get_role(self, obj: Any) -> dict | None:
        profile = getattr(obj, "docuparse_profile", None)
        if not profile or not profile.role_ref:
            return None
        return {"id": str(profile.role_ref.id), "name": profile.role_ref.name}


class UserCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role_id = serializers.UUIDField()

    def validate_email(self, value: str) -> str:
        User = get_user_model()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este e-mail já está em uso.")
        return value

    def validate_role_id(self, value: Any) -> Role:
        try:
            return Role.objects.get(id=value)
        except Role.DoesNotExist:
            raise serializers.ValidationError("Role não encontrada.")

    def create(self, validated_data: dict) -> Any:
        from documents.models import Tenant, UserProfile
        User = get_user_model()
        role: Role = validated_data["role_id"]
        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["name"],
            is_active=True,
        )
        tenant = Tenant.objects.first()
        UserProfile.objects.create(user=user, tenant=tenant, role_ref=role)
        return user


class UserUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    role_id = serializers.UUIDField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)

    def validate_role_id(self, value: Any) -> Role | None:
        if value is None:
            return None
        try:
            return Role.objects.get(id=value)
        except Role.DoesNotExist:
            raise serializers.ValidationError("Role não encontrada.")


# ─── Role Management Serializers ──────────────────────────────────────────────

class RoleListSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    permissions = serializers.SerializerMethodField()
    users_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField()

    def get_permissions(self, obj: Any) -> list[str]:
        return list(obj.permissions.values_list("code", flat=True))


class RoleCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    permission_codes = serializers.ListField(child=serializers.CharField(), min_length=1)

    def validate_name(self, value: str) -> str:
        from users.models import Role
        if Role.objects.filter(name=value).exists():
            raise serializers.ValidationError("Já existe uma role com este nome.")
        return value

    def validate_permission_codes(self, value: list[str]) -> list[str]:
        from users.models import Permission
        if not value:
            raise serializers.ValidationError("Uma role deve ter ao menos uma permissão.")
        for code in value:
            if not Permission.objects.filter(code=code).exists():
                raise serializers.ValidationError(f"Permissão '{code}' não existe.")
        return value


class RoleUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128, required=False)
    permission_codes = serializers.ListField(child=serializers.CharField(), min_length=1, required=False)

    def validate_permission_codes(self, value: list[str]) -> list[str]:
        from users.models import Permission
        if not value:
            raise serializers.ValidationError("Uma role deve ter ao menos uma permissão.")
        for code in value:
            if not Permission.objects.filter(code=code).exists():
                raise serializers.ValidationError(f"Permissão '{code}' não existe.")
        return value


# ─── Register Serializer ──────────────────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value: str) -> str:
        User = get_user_model()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este e-mail já está em uso.")
        return value
