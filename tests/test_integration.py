import unittest
import requests
from pathlib import Path
from miku.config import OLLAMA_URL, DEFAULT_MODEL, DATA
from miku.memory import remember, history, add_memory, search_memory, delete_memory
from miku.tools import read_file, create_file, launch_app, ollama_tools, browser_search
import pyautogui

class Integration(unittest.TestCase):
    def tearDown(self):
        import sqlite3
        db=sqlite3.connect(DATA/'miku.sqlite3')
        try:
            db.execute("DELETE FROM messages WHERE content='integration conversation check'")
            db.execute("DELETE FROM memories WHERE content='integration memory sentinel 73a8'")
            db.commit()
        finally: db.close()
    def test_ollama_and_local_inference(self):
        tags=requests.get(OLLAMA_URL+'/api/tags',timeout=5).json()['models']
        self.assertIn(DEFAULT_MODEL,{m['name'] for m in tags})
        result=requests.post(OLLAMA_URL+'/api/chat',json={'model':DEFAULT_MODEL,'messages':[{'role':'user','content':'Reply exactly READY.'}],'stream':False,'options':{'num_ctx':512,'num_predict':64,'temperature':0}},timeout=180).json()
        self.assertIn('READY',result['message'].get('content','').upper())

    def test_ollama_tool_call(self):
        result=requests.post(OLLAMA_URL+'/api/chat',json={'model':DEFAULT_MODEL,'messages':[{'role':'user','content':'Use the launch_app tool with name Notepad.'}],'tools':ollama_tools(),'stream':False,'options':{'num_ctx':1024,'num_predict':96,'temperature':0}},timeout=180).json()
        self.assertEqual(result['message']['tool_calls'][0]['function']['name'],'launch_app')

    def test_browser_navigation_and_read(self):
        text=browser_search('local inference software news')
        self.assertGreater(len(text),100)

    def test_tool_registry_and_file_create_read_edit(self):
        self.assertIn('launch_app',{t['function']['name']:t for t in ollama_tools()})
        path=str(DATA/'integration-check.txt')
        create_file(path,'first')
        self.assertEqual(read_file(path),'first')
        create_file(path,'edited')
        self.assertEqual(read_file(path),'edited')
        Path(path).unlink()
        for backup in DATA.glob('integration-check.txt.miku-backup-*'): backup.unlink()

    def test_sqlite_memory_persistence(self):
        phrase='integration memory sentinel 73a8'
        add_memory(phrase)
        self.assertTrue(any(phrase in x for x in search_memory('sentinel 73a8')))
        self.assertEqual(delete_memory('sentinel 73a8'),1)
        remember('user','integration conversation check')
        self.assertEqual(history(1)[-1]['content'],'integration conversation check')

    def test_screenshot(self):
        im=pyautogui.screenshot()
        self.assertGreater(im.width,0); self.assertGreater(im.height,0)

    def test_launch_notepad(self):
        import subprocess, time
        before={p.pid for p in __import__('psutil').process_iter(['name']) if (p.info.get('name') or '').lower()=='notepad.exe'}
        launch_app('Notepad')
        time.sleep(2)
        after={p.pid for p in __import__('psutil').process_iter(['name']) if (p.info.get('name') or '').lower()=='notepad.exe'}
        self.assertTrue(after-before or after)

if __name__=='__main__': unittest.main(verbosity=2)
