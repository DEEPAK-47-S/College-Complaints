from django.urls import path
from . import public_views

app_name = 'public'

urlpatterns = [
    path('', public_views.public_index_view, name='index'),
    path('complaint/', public_views.public_submit_view, name='submit'),
    path('complaint/send-otp/', public_views.send_otp_api, name='send_otp'),
    path('complaint/verify-otp/', public_views.verify_otp_api, name='verify_otp'),
    path('complaint/success/<str:complaint_no>/', public_views.public_success_view, name='success'),
    path('track/', public_views.public_track_view, name='track'),
    path('complaint/<str:complaint_no>/', public_views.public_detail_view, name='detail'),
    path('track/<str:complaint_no>/', public_views.public_detail_view, name='track_detail'),
]

