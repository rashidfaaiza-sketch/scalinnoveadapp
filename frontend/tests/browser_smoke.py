from playwright.sync_api import sync_playwright
from pathlib import Path
import json
import os
import uuid
errors=[]
suffix=uuid.uuid4().hex[:8]
project_name=f'Smoke campaign {suffix}'
video_name=f'Smoke video {suffix}'
final_name=f'Smoke final {suffix}'
base_url=os.environ.get('BASE_URL','http://localhost:5173')
password=os.environ['WORKSPACE_PASSWORD']
output=Path(os.environ.get('SCREENSHOT_DIR','/tmp/forma-checks'))
output.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or None,headless=True,args=['--no-sandbox'] if os.environ.get('CHROMIUM_NO_SANDBOX')=='true' else [])
 page=browser.new_page(viewport={'width':1440,'height':1100})
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(base_url)
 page.get_by_label('Workspace password').fill(password)
 page.get_by_role('button',name='Enter studio').click()
 page.get_by_role('heading',name='Good ideas deserve great ads.').wait_for()
 page.screenshot(path=str(output/'desktop.png'),full_page=True)
 page.get_by_role('button',name='Create a video',exact=True).first.click()
 page.get_by_role('button',name='New project',exact=True).click()
 page.get_by_label('Project name',exact=True).fill(project_name)
 page.get_by_label('Product or service',exact=True).fill('Loop reusable bottle')
 page.get_by_label('Target audience',exact=True).fill('Design-conscious commuters')
 page.get_by_label('Ad objective',exact=True).fill('Introduce our reusable bottle')
 page.get_by_role('button',name='Create project',exact=True).click()
 page.get_by_role('button',name='Draft ad script',exact=True).click()
 page.get_by_label('The hook').wait_for()
 page.wait_for_function("document.querySelector('textarea').value.length > 0")
 page.get_by_label('Video name',exact=True).fill(video_name)
 page.screenshot(path=str(output/'creator.png'),full_page=True)
 page.get_by_role('button',name='Create free video',exact=True).click()
 page.get_by_role('heading',name='Made by you. Ready to move.').wait_for()
 page.get_by_role('button',name=f'Open {video_name}',exact=True).click()
 if page.locator('video.video-player').count()==0:
  page.get_by_role('button',name='Watch video',exact=True).wait_for(timeout=90000)
  page.get_by_role('button',name='Watch video',exact=True).click()
 player=page.locator('video.video-player')
 player.wait_for()
 page.wait_for_function("document.querySelector('video.video-player').readyState >= 2")
 assert player.evaluate('(v)=>v.videoWidth')==720
 page.get_by_label('Export aspect ratio').select_option('1:1')
 with page.expect_download() as download_info:
  page.get_by_role('button',name='Export MP4',exact=True).click()
 download_info.value.save_as(str(output/'browser-export.mp4'))
 page.get_by_role('button',name='Close dialog').click()
 page.get_by_role('button',name=f'Rename {video_name}').click()
 page.get_by_label('Video name',exact=True).fill(final_name)
 page.get_by_role('button',name='Save name',exact=True).click()
 page.get_by_role('heading',name=final_name,exact=True).wait_for()
 page.get_by_role('button',name='Studio settings').click()
 page.get_by_role('heading',name='Your studio, connected.').wait_for()
 page.get_by_role('button',name='Projects',exact=True).click()
 page.get_by_role('heading',name=project_name,exact=True).wait_for()
 page.set_viewport_size({'width':390,'height':844})
 page.get_by_role('button',name='Open navigation').click()
 page.get_by_role('button',name='Overview',exact=True).click()
 page.wait_for_timeout(600)
 page.screenshot(path=str(output/'mobile.png'),full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Horizontal overflow on mobile'
 print(json.dumps({'browser_errors':errors,'video_playback':True,'mobile_overflow':False}))
 browser.close()
assert not errors
