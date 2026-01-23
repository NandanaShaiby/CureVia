from django.urls import path, include
from myapp import views


urlpatterns =[
        path('', views.index),
        path('reg/', views.reg),
        path('login/', views.login ,name='login'),
        path('adminp/', views.admin),
        path('user/', views.user),
        path('pharmacist/', views.pharmacist),
        path('customer/', views.customer),
        path('blockuser/<id>/',views.blockuser ),
        path('unblock/<id>/',views.unblock ),
        path('edituser/<int:id>/', views.edituser, name='edit_user'),
        path('adduser/', views.adduser, name='add_user'),
        path('addmed/', views.addmed,),
        path('shop/', views.shop),
        path('about/', views.about),
        path('contact/', views.contact),
        path('userprofile/<int:id>/', views.userprofile, name='userprofile'),
        path('shop/<int:id>/', views.single_product, name='single_product'),
        path('cart/', views.cart),
        path('addcart/<id>/',views.addcart),
        path('deletecart/<id>/',views.deletecart),
        path('checkout/',views.checkout),
        path('payment/',views.payment),
        path('confirmpayment/',views.confirmpayment),
        path('thanku/',views.thanku),
        path('search/', views.search_product, name='search'),
        path('upload_prescription/<int:id>/', views.upload_prescription, name='upload_prescription'),
        path('view_prescriptions/', views.view_prescriptions, name='view_prescriptions'),
        path('view_general_prescriptions/', views.view_general_prescriptions, name='view_general_prescriptions'),
        path('approve_prescription/<int:id>/', views.approve_prescription, name='approve_prescription'),
        path('reject_prescription/<int:id>/', views.reject_prescription, name='reject_prescription'),
        path('upload_general/', views.upload_general, name='upload_general'),
        path('delivery_home/', views.delivery_home, name='delivery_home'),
        path('pharmacies/', views.pharmacies),
        path('blockpharmacy/<int:id>/',views.blockpharmacy, name='block_pharmacy' ),
        path('unblockpharmacy/<int:id>/',views.unblockpharmacy, name='unblock_pharmacy' ),
        path('editpharmacy/<int:id>/', views.editpharmacy, name='edit_pharmacy'),
        path('addpharmacy/', views.addpharmacy, name='add_pharmacy'),
        path('admin_products/', views.admin_products, name='admin_products'),
        path('lock_and_process/<int:id>/', views.lock_and_process, name='lock_and_process'),
        path('process_prescription/<int:id>/', views.process_prescription, name='process_prescription'),
        path('add_pres_item/<int:pres_id>/', views.add_pres_item, name='add_pres_item'),
        path('remove_pres_item/<int:item_id>/', views.remove_pres_item, name='remove_pres_item'),
        path('submit_to_user/<int:pres_id>/', views.submit_to_user, name='submit_to_user'),
        path('mark_processed/<int:pres_id>/', views.mark_processed, name='mark_processed'),
        path('transfer_prescription/<int:id>/', views.transfer_prescription, name='transfer_prescription'),
        path('my_prescriptions/', views.my_prescriptions, name='my_prescriptions'),
        path('review_prescription/<int:id>/', views.review_prescription, name='review_prescription'),
        path('confirm_prescription_order/<int:id>/', views.confirm_prescription_order, name='confirm_prescription_order'),
        path('reject_quote/<int:id>/', views.reject_quote, name='reject_quote'),
        path('process_order_action/<int:id>/', views.process_order_action, name='process_order_action'),
        path('process_group_order/<str:group_id>/', views.process_group_order, name='process_group_order'),
        path('pharmacy_staff_login/', views.pharmacy_staff_login, name='pharmacy_staff_login'),
        path('update_pincode/', views.update_pincode, name='update_pincode'),
        path('inventory/', views.pharmacy_inventory, name='pharmacy_inventory'),
        path('update_inventory/<int:id>/', views.update_inventory, name='update_inventory'),
        path('delete_medicine/<int:id>/', views.delete_medicine, name='delete_medicine'),
        path("chatbot/", include("chatbot.urls")),
        path('my_orders/', views.my_orders, name='my_orders'),
        path('track_order/<str:group_id>/', views.track_order, name='track_order'),
        path('delivery_update_status/<int:id>/', views.delivery_update_status, name='delivery_update_status'),
        path('toggle_agent_status/', views.toggle_agent_status, name='toggle_agent_status'),









path('forgotpass/',views.forgotpass),






    ]