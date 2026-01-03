import os
import json
import subprocess
from http.server import BaseHTTPRequestHandler
import urllib.parse
from api.shared import *

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Parse query parameters
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            file_id = params.get('file_id', [''])[0]
            
            if not file_id:
                self.send_error(400, 'Missing file_id parameter')
                return
            
            files_data = load_data()
            
            if file_id not in files_data:
                self.send_error(404, 'File not found')
                return
            
            file_info = files_data[file_id]
            
            # Check password if needed
            if file_info['is_private'] and file_info['has_password']:
                # Check if password is provided
                password = params.get('password', [''])[0]
                
                if not password:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    html = f'''
                    <html>
                    <body>
                        <h3>Password Required to Execute</h3>
                        <form method="GET">
                            <input type="hidden" name="file_id" value="{file_id}">
                            <input type="password" name="password" placeholder="Enter password" required>
                            <button type="submit">Execute File</button>
                        </form>
                    </body>
                    </html>
                    '''
                    self.wfile.write(html.encode())
                    return
                
                # Verify password
                passwords_data = load_passwords()
                if file_id not in passwords_data or \
                   passwords_data[file_id] != hash_password(password):
                    self.send_error(403, 'Invalid password')
                    return
            
            # Execute the file
            file_path = os.path.join(UPLOAD_FOLDER, file_info['saved_name'])
            
            if os.path.exists(file_path):
                try:
                    # Run Python file with timeout
                    result = subprocess.run(
                        ['python', file_path],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    output = f"Exit Code: {result.returncode}\n\n"
                    output += "STDOUT:\n" + result.stdout + "\n\n"
                    output += "STDERR:\n" + result.stderr
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(output.encode())
                    
                except subprocess.TimeoutExpired:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write("Execution timed out (10 seconds)".encode())
                    
                except Exception as e:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(f"Execution error: {str(e)}".encode())
            else:
                self.send_error(404, 'File not found')
                
        except Exception as e:
            self.send_error(500, f'Server error: {str(e)}')
