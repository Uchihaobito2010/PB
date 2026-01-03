import os
import json
import base64
from http.server import BaseHTTPRequestHandler
import urllib.parse
from api.shared import *

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Parse query parameters
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            file_id = params.get('file_id', [''])[0]
            
            if not file_id:
                self.send_error(400, 'Missing file_id parameter')
                return
            
            # Parse request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            filename = data.get('filename')
            content = data.get('content')
            password = data.get('password', '')
            
            if not filename or not content:
                self.send_error(400, 'Missing filename or content')
                return
            
            # Check if file exists
            files_data = load_data()
            if file_id not in files_data:
                self.send_error(404, 'File not found')
                return
            
            file_info = files_data[file_id]
            
            # Check password if private
            if file_info['is_private'] and file_info['has_password']:
                passwords_data = load_passwords()
                
                if file_id not in passwords_data or \
                   passwords_data[file_id] != hash_password(password):
                    self.send_error(403, 'Invalid password')
                    return
            
            # Update the file
            save_filename = f"{file_id}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, save_filename)
            
            # Decode and save file
            file_content = base64.b64decode(content)
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Update metadata
            files_data[file_id] = {
                'original_name': filename,
                'saved_name': save_filename,
                'upload_time': datetime.now().isoformat(),
                'is_private': file_info['is_private'],
                'has_password': file_info['has_password']
            }
            
            save_data(files_data)
            
            # Get base URL
            base_url = f"{self.headers.get('X-Forwarded-Proto', 'https')}://{self.headers.get('Host')}"
            
            response = {
                'message': 'File updated successfully',
                'raw_url': f"{base_url}/api/raw?file_id={file_id}",
                'execute_url': f"{base_url}/api/execute?file_id={file_id}"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_error(500, f'Server error: {str(e)}')
