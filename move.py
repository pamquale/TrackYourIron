import os, shutil
root_dir = r'D:\dev\TrackYourIron'
src_dir = os.path.join(root_dir, 'notification_service')
os.makedirs(os.path.join(root_dir, 'bot', 'src'), exist_ok=True)
os.makedirs(os.path.join(root_dir, 'scraper'), exist_ok=True)
os.makedirs(os.path.join(root_dir, 'gateway'), exist_ok=True)

for f in ['bot', 'db', 'services', 'config.py', 'main.py', '__init__.py']:
    try: shutil.move(os.path.join(src_dir, f), os.path.join(root_dir, 'bot', 'src', f))
    except Exception as e: pass

scraper_src = os.path.join(src_dir, 'TrackYourIron-scraper-service')
if os.path.exists(scraper_src):
    for f in os.listdir(scraper_src):
        try: shutil.move(os.path.join(scraper_src, f), os.path.join(root_dir, 'scraper', f))
        except: pass

gateway_src = os.path.join(src_dir, 'TrackYourIron-feature-api-gateway')
if os.path.exists(gateway_src):
    for f in os.listdir(gateway_src):
        try: shutil.move(os.path.join(gateway_src, f), os.path.join(root_dir, 'gateway', f))
        except: pass

infra_src = os.path.join(src_dir, 'TrackYourIron-feature-infrastructure')
if os.path.exists(infra_src):
    for f in os.listdir(infra_src):
        try: shutil.move(os.path.join(infra_src, f), os.path.join(root_dir, f))
        except: pass
