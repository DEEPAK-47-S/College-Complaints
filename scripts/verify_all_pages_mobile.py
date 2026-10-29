import os
import sys
import time
import threading
from wsgiref.simple_server import make_server

# Set up Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'
import django
django.setup()

from django.core.wsgi import get_wsgi_application
from apps.complaints.models import Complaint
from playwright.sync_api import sync_playwright

PORT = 8011
BASE_URL = f"http://127.0.0.1:{PORT}"

def start_server():
    app = get_wsgi_application()
    server = make_server('127.0.0.1', PORT, app)
    server.serve_forever()

# Start background WSGI server
server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()
time.sleep(1.5)

# Get or find a sample complaint for detail & success testing
complaint = Complaint.objects.first()
complaint_no = complaint.complaint_no if complaint else "AICTE-2026-PGRC-00001"

pages_to_test = [
    ('/', 'Homepage'),
    ('/complaint/', 'Submit Grievance'),
    ('/track/', 'Track Status'),
    (f'/complaint/{complaint_no}/', 'Complaint Detail'),
    (f'/complaint/success/{complaint_no}/', 'Submission Success'),
    ('/accounts/login/', 'Officer Login'),
]

viewports = [
    {'name': 'Mobile Small (360x640)', 'width': 360, 'height': 640},
    {'name': 'iPhone 13 (390x844)', 'width': 390, 'height': 844},
    {'name': 'Mobile Large (412x915)', 'width': 412, 'height': 915},
    {'name': 'Tablet (768x1024)', 'width': 768, 'height': 1024},
    {'name': 'Desktop (1280x800)', 'width': 1280, 'height': 800},
]

print("=" * 80)
print("STARTING FULL MOBILE ADAPTIVE & COMPREHENSIVE PAGE VERIFICATION")
print("=" * 80)

total_checks = 0
failed_checks = 0

with sync_playwright() as p:
    browser = p.chromium.launch()
    
    # 1. First test logo & favicon directly
    test_page = browser.new_page()
    for static_asset in ['/static/icon/logo.svg', '/static/icon/favicon.svg', '/static/icon/favicon.ico', '/favicon.ico']:
        url = f"{BASE_URL}{static_asset}"
        resp = test_page.goto(url)
        status = resp.status if resp else 0
        total_checks += 1
        if status in (200, 301, 302):
            print(f"  [PASS] Asset Check: {static_asset} -> HTTP {status}")
        else:
            print(f"  [FAIL] Asset Check: {static_asset} -> HTTP {status}")
            failed_checks += 1
    test_page.close()

    # 2. Test each page across all viewports
    for vp in viewports:
        print(f"\n--- Testing Viewport: {vp['name']} ---")
        page = browser.new_page(viewport={'width': vp['width'], 'height': vp['height']})
        
        for path, name in pages_to_test:
            total_checks += 1
            url = f"{BASE_URL}{path}"
            resp = page.goto(url, wait_until='networkidle')
            status = resp.status if resp else 0
            
            # Check horizontal scroll overflow
            scroll_width = page.evaluate('document.documentElement.scrollWidth')
            client_width = page.evaluate('document.documentElement.clientWidth')
            has_overflow = scroll_width > client_width
            
            # Check if brand logo image is present and visible
            has_logo = False
            if path in ('/', '/complaint/', '/track/', f'/complaint/{complaint_no}/'):
                logo_el = page.query_selector('.public-brand-img')
                if logo_el and logo_el.is_visible():
                    has_logo = True
            else:
                has_logo = True # Skip for officer login

            if status == 200 and not has_overflow and has_logo:
                print(f"  [PASS] {name} ({path}): HTTP 200, scrollWidth={scroll_width} (No Overflow), Logo=OK")
            else:
                print(f"  [FAIL] {name} ({path}): HTTP {status}, Overflow={has_overflow} (scroll={scroll_width}, client={client_width}), Logo={has_logo}")
                failed_checks += 1

        # Test mobile drawer interaction on small screens
        if vp['width'] < 768:
            page.goto(f"{BASE_URL}/", wait_until='networkidle')
            menu_btn = page.query_selector('#mobileMenuBtn')
            drawer = page.query_selector('#mobileNavDrawer')
            total_checks += 1
            if menu_btn and drawer:
                is_vis_1 = drawer.is_visible()
                menu_btn.click()
                time.sleep(0.2)
                is_vis_2 = drawer.is_visible()
                menu_btn.click()
                time.sleep(0.2)
                is_vis_3 = drawer.is_visible()
                
                if not is_vis_1 and is_vis_2 and not is_vis_3:
                    print(f"  [PASS] Mobile Navigation Drawer: opens and closes properly on click!")
                else:
                    print(f"  [FAIL] Mobile Drawer toggle states: before={is_vis_1}, open={is_vis_2}, closed={is_vis_3}")
                    failed_checks += 1

        page.close()
    
    browser.close()

print("\n" + "=" * 80)
print(f"VERIFICATION SUMMARY: {total_checks - failed_checks}/{total_checks} checks PASSED! Failed: {failed_checks}")
print("=" * 80)
if failed_checks > 0:
    sys.exit(1)

