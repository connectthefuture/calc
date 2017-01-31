from django.conf import settings


def api_host(request):
    '''Include API_HOST in all request contexts'''
    return {'API_HOST': settings.API_HOST}


def show_debug_ui(request):
    '''Include show_debug_ui in all request contexts'''
    return {'show_debug_ui': settings.DEBUG and not settings.HIDE_DEBUG_UI}


def google_analytics_tracking_id(request):
    '''Include GA_TRACKING_ID in all request contexts'''
    return {'GA_TRACKING_ID': settings.GA_TRACKING_ID}


def ethnio_screener_id(request):
    '''Include ETHNIO_SCREENER_ID in all request contexts'''
    return {'ETHNIO_SCREENER_ID': settings.ETHNIO_SCREENER_ID}


def help_email(request):
    '''Include HELP_EMAIL in all request contexts'''
    return {'HELP_EMAIL': settings.HELP_EMAIL}


def non_prod_instance_name(request):
    '''Include NON_PROD_INSTANCE_NAME in all request contexts'''
    return {'NON_PROD_INSTANCE_NAME': settings.NON_PROD_INSTANCE_NAME}
