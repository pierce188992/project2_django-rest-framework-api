"""
Views for the recipe APIs
"""
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
)
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import Recipe, Tag, Ingredient
from recipe import serializers

"""
@extend_schema_view: 這是一個修飾器，用於擴展視圖中的某些操作的模式。

list=extend_schema(...): 這指示我們要擴展的操作是 list 操作。
在 DRF 中，這通常是 GET 請求到列表端點。

parameters: 這是一個列表，指定要添加到操作的額外參數。

OpenApiParameter: 用於定義一個新的 API 參數。
第一個參數是參數的名稱，例如 "tags"。
OpenApiTypes.STR: 這指定參數的數據類型是字符串。 i.e. "tags" = "8,9"
description: 這是參數的描述。
"""


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "tags",
                OpenApiTypes.STR,
                description="Comma separated list of tag IDs to filter",
            ),
            OpenApiParameter(
                "ingredients",
                OpenApiTypes.STR,
                description="Comma separated list of ingredient IDs to filter",
            ),
        ]
    )
)
class RecipeViewSet(viewsets.ModelViewSet):
    """View for manage recipe APIs."""

    serializer_class = serializers.RecipeDetailSerializer
    """
    序列化器首先將複雜的數據類型（例如 Django 的查詢集或模型實例）轉換為 Python 的原生數據結構（例如字典、列表、字符串、整數等）。
    然後，然後這些原生數據結構再進一步被轉換為不同的內容格式，如 JSON、XML 等。DRF 默認使用 JSON 格式
    1.ModelViewSet，很多序列化和反序列化的工作都會自動完成。
    2.ModelViewSet（或大多數其他內置的 DRF 視圖）時，它的預設行為是期望請求主體中的數據為 JSON 格式。這是因為：

    易於使用：JSON 是一種常見的數據格式，它易於使用且在多個平台和語言中都有支持。
    標準化：使用 JSON 作為標準格式可以確保 API 的一致性，無論調用者在哪裡或使用什麼技術。
    內置支持：DRF 內置了 JSONParser，這是一個專門用於解析 JSON 請求主體的解析器。

    """
    queryset = Recipe.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _params_to_ints(self, qs):
        """Convert a list of strings to integers."""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        tags = self.request.query_params.get("tags")
        ingredients = self.request.query_params.get("ingredients")
        queryset = self.queryset
        if tags:
            # print(tags) # 8,9 字串
            tag_ids = self._params_to_ints(tags)
            # print(tag_ids) # [8, 9] 數字列表
            queryset = queryset.filter(tags__id__in=tag_ids)
            """
            tags：這是模型中的多對多字段名稱，表示食譜與標籤之間的關係。
            __id：這是查詢關聯對象的 ID 屬性。在這裡，它是指標籤模型的 ID。
            __in：這是 Django 查詢語法中的一個過濾器，表示我們要查找的值應該在給定的列表中。
            """
        if ingredients:
            ingredient_ids = self._params_to_ints(ingredients)
            queryset = queryset.filter(ingredients__id__in=ingredient_ids)

        return queryset.filter(user=self.request.user).order_by("-id").distinct()
        # """Retrieve recipes for authenticated user."""
        # return self.queryset.filter(user=self.request.user).order_by("-id")

    def get_serializer_class(self):
        """Return the serializer class for request."""
        if self.action == "list":
            return serializers.RecipeSerializer
        elif self.action == "upload_image":
            return serializers.RecipeImageSerializer

        return self.serializer_class

    def perform_create(self, serializer):
        """Create a new recipe."""
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """Update a recipe."""
        serializer.save(user=self.request.user)

    """
    @action 裝飾器用來定義一個自定義的動作。
    methods=["POST"] 表示這個動作只接受 POST 請求。
    detail=True 表示這是一個針對特定對象的動作，而不是針對整個查詢集。
    url_path="upload-image" 定義了該動作的 URL 路徑。
    """

    @action(methods=["POST"], detail=True, url_path="upload-image")
    def upload_image(self, request, pk=None):
        """Upload an image to recipe."""
        recipe = (
            self.get_object()
        )  # 根據當前視圖的查詢集 (queryset) 和提供的 URL 參數（例如，在 URL 中的主鍵或 slug）來獲取和返回一個單一的對象。
        serializer = self.get_serializer(recipe, data=request.data)
        """
        self.get_serializer() 會根據當前的視圖操作（例如 "list", "create", "upload_image" 等）返回適當的序列化器類。
        recipe: 這是傳遞給序列化器的第一個參數，它表示要進行序列化或反序列化的對象。
        data=request.data: 這是建立序列化器時傳遞的 data 參數，
        它包含客戶端提交的數據。在此情境下，它可能包含要上傳的圖片數據。
        DRF 會使用這些數據來驗證和保存/更新 recipe 對象。
        """
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    """
    create 方法處理 POST 請求的邏輯，它是用於創建資料的主要方法。
    這個方法首先會初始化序列化器，檢查序列化器是否有效，然後保存資料。
    它還負責返回適當的響應，如成功的 201 Created 或錯誤的 400 Bad Request。
    perform_create:

    perform_create 是 create 方法中用來實際保存模型實例的部分。
    它的主要目的是提供一個可以輕鬆覆蓋的方法，以自定義保存行為，而無需重寫整個 create 方法。
    例如，如果你想在保存之前設置某些屬性或觸發某些操作，你可以覆蓋 perform_create。

    #其他方法
    perform_create 只在 POST 請求（對應於創建操作）時被觸發。但 ModelViewSet 提供了其他方法，
    這些方法允許您在執行 CRUD 操作之前或之後插入自定義邏輯, 可以在其他請求中被覆寫和觸發：

    POST (Create): perform_create(self, serializer)
    在這個方法中，一個新的實例被創建和保存。

    PUT (Update): perform_update(self, serializer)
    此方法在一個已存在的實例被完全更新時被觸發。

    PATCH (Partial Update): perform_update(self, serializer)
    這也會觸發 perform_update，但與 PUT 不同的是，它僅更新提供的字段，而不是整個實例。

    DELETE (Destroy): perform_destroy(self, instance)
    在此方法中，給定的實例被刪除。
    """


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "assigned_only",
                OpenApiTypes.INT,
                enum=[0, 1],
                description="Filter by items assigned to recipes.",
            ),
        ]
    )
)
class BaseRecipeAttrViewSet(
    mixins.DestroyModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Base viewset for recipe attributes."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter queryset to authenticated user."""
        assigned_only = bool(int(self.request.query_params.get("assigned_only", 0)))
        queryset = self.queryset
        if assigned_only:
            queryset = queryset.filter(recipe__isnull=False)
            # 與至少一個食譜相關聯的項目（即，其關聯的食譜不是空的）。
        return queryset.filter(user=self.request.user).order_by("-name").distinct()


class TagViewSet(BaseRecipeAttrViewSet):
    """Manage tags in the database."""

    serializer_class = serializers.TagSerializer
    queryset = Tag.objects.all()


class IngredientViewSet(BaseRecipeAttrViewSet):
    """Manage ingredients in the database."""

    serializer_class = serializers.IngredientSerializer
    queryset = Ingredient.objects.all()


# 分開的寫法
# class TagViewSet(
#     mixins.DestroyModelMixin,
#     mixins.UpdateModelMixin,
#     mixins.ListModelMixin,
#     viewsets.GenericViewSet,
# ):
#     """Manage tags in the database."""

#     serializer_class = serializers.TagSerializer
#     queryset = Tag.objects.all()
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         """Filter queryset to authenticated user."""
#         return self.queryset.filter(user=self.request.user).order_by("-name")


# class IngredientViewSet(
#     mixins.DestroyModelMixin,
#     mixins.UpdateModelMixin,
#     mixins.ListModelMixin,
#     viewsets.GenericViewSet,
# ):
#     """Manage ingredients in the database."""

#     serializer_class = serializers.IngredientSerializer
#     queryset = Ingredient.objects.all()
#     authentication_classes = [TokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         """Filter queryset to authenticated user."""
#         return self.queryset.filter(user=self.request.user).order_by("-name")


"""
mixins.ListModelMixin:
這個 mixin 提供了將查詢集列出為一個列表的功能。
當您的視圖集接收到一個 GET 請求時，如果視圖集繼承了 ListModelMixin，
那麼這個 mixin 中的 list 方法會被調用，返回查詢集的列表。

viewsets.GenericViewSet:
這是 DRF 的一個基本視圖集。它提供了視圖集的核心功能，
例如 get_object、get_serializer 等方法，但不包含任何特定的動作，
如 create、update、delete 等。這意味著，單獨使用 GenericViewSet 不會提供 CRUD 操作。
但是，當它與其他 mixins（如 ListModelMixin、CreateModelMixin、UpdateModelMixin 等）組合時，
它可以用來創建具有特定功能的視圖集。

1.Mixins:
目的: Mixins 的主要目的是提供單一、特定的功能。例如，提供對象創建、檢索、更新或刪除的功能。
組合性: 通常，多個 mixins 可以被組合在一起，以在單一的視圖中提供多個功能。
常見的 Mixins:
ListModelMixin: 提供列表視圖功能。
CreateModelMixin: 提供對象創建功能。
RetrieveModelMixin: 提供單一對象的檢索功能。
UpdateModelMixin: 提供對象更新功能。
DestroyModelMixin: 提供對象刪除功能。
使用方式: Mixins 被設計為與其他視圖基礎類組合使用，如 GenericAPIView。

2.Viewsets:
目的: Viewsets 是用來表示一組完整的 CRUD (Create, Retrieve, Update, Delete) 操作的。它們通常與模型和序列化器一起使用。
簡化性: Viewsets 的目的是簡化常見的模型視圖模式。
常見的 Viewsets:
ModelViewSet: 它包含了 CRUD 操作的全部方法。實際上，ModelViewSet 繼承了多個 mixins，給出了完整的 CRUD 功能。
ReadOnlyModelViewSet: 只提供列表和檢索操作。
使用方式: Viewsets 被設計為與 DRF 的 routers 一起使用，以自動生成 URL 模式。

3.結論:
mixins 是較小的、功能單一的組件，通常與其他視圖基礎類組合使用，以提供所需的功能。
viewsets 提供一組完整的 CRUD 操作，通常與 DRF 的 routers 一起使用，以自動生成 URL 模式。
"""


# 發送請求的方式
"""
import requests

url = "http://127.0.0.1:8000/api/recipe/recipes/"
headers = {
    "accept": "application/json",
    "Authorization": "Token 4159325a68f6b0c3548de9ef8ba9007d96b57e26",
    "X-CSRFToken": "j0NuS2tGKvRF2yOaGmGC028ZyulnmOehBLrzQEZAQTSYUdDlLUBZ8nsBOxL1KYKM", # get方法不需要
}

response = requests.get(url, headers=headers)

# 處理響應
if response.status_code == 200:
    print(response.json())  # 如果返回的是 JSON 數據
else:
    print("Error:", response.status_code)
"""
