from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryListView, OfferViewSet, ProductSearchView, ProductViewSet,
    CategoryViewSet, SubCategoryViewSet, CategorySizeViewSet,
    ProductListView, ProductDetailView, ProductCategoryFilterView, ProductSubCategoryFilterView, ProductFilterByCategoryView
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubCategoryViewSet)
router.register(r'categorysizes', CategorySizeViewSet)
router.register(r'offers', OfferViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('customer/products/', ProductListView.as_view(), name='product-list'),
    path('customer/category/', CategoryListView.as_view(), name='category-list'),
    path('customer/products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('customer/products/category/<int:category_id>/', ProductCategoryFilterView.as_view(), name='product-category-filter'),
    path('customer/products/subcategory/<int:subcategory_id>/', ProductSubCategoryFilterView.as_view(), name='product-subcategory-filter'),
    path('customer/products/search/', ProductSearchView.as_view(), name='product-search'),
    path('customer/products/filter-by-category/', ProductFilterByCategoryView.as_view(), name='product-filter-by-category'),

]
