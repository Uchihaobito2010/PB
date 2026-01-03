import os
import json
from http.server import BaseHTTPRequestHandler
import urllib.parse
from api.shared import *
import base64

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Python Pastebin</title>
            <style>
                body { font-family: Arial; max-width: 600px; margin: 0 auto; padding: 20px; }
                input, button { padding: 10px; margin: 5px 0; width: 100%; }
                .private-options { margin: 15px 0; }
            </style>
        </head>
        <body>
            <h1>Upload Python File</h1>
            <form id="uploadForm">
                <input type="file" id="fileInput" accept=".py" required><br><br>
                
                <label>
                    <input type="checkbox" id="isPrivate"> Make Private
                </label><br><br>
                
                <div id="passwordField" style="display: none;">
                    <input type="password" id="password" placeholder="Set password">
                </div><br>
                
                <button type="button" onclick="uploadFile()">Upload</button>
            </form>
            
            <div id="result" style="margin-top: 20px;"></div>
            
            <script>
                document.getElementById('isPrivate').addEventListener('change', function() {
                    document.getElementById('passwordField').style.display = 
                        this.checked ? 'block' : 'none';
                });
                
                async function uploadFile() {
                    const fileInput = document.getElementById('fileInput');
                    const isPrivate = document.getElementById('isPrivate').checked;
                    const password = document.getElementById('password').value;
                    
                    if (!fileInput.files[0]) {
                        alert('Please select a file');
                        return;
                    }
                    
                    const file = fileInput.files[0];
                    
                    // Check if Python file
                    if (!file.name.endsWith('.py')) {
                        alert('Only Python files (.py) are allowed');
                        return;
                    }
                    
                    const reader = new FileReader();
                    reader.onload = async function(e) {
                        const content = e.target.result;
                        const base64Content = btoa(content);
                        
                        const formData = new FormData();
                        formData.append('filename', file.name);
                        formData.append('content', base64Content);
                        formData.append('is_private', isPrivate);
                        formData.append('password', password);
                        
                        try {
                            const response = await fetch('/api/upload', {
                                method: 'POST',
                                body: JSON.stringify({
                                    filename: file.name,
                                    content: base64Content,
                                    is_private: isPrivate,
                                    password: password
                                }),
                                headers: {
                                    'Content-Type': 'application/json'
                                }
                            });
                            
                            const result = await response.json();
                            
                            if (response.ok) {
                                document.getElementById('result').innerHTML = `
                                    <h3>Upload Successful!</h3>
                                    <p><strong>File ID:</strong> ${result.file_id}</p>
                                    <p><strong>Raw URL:</strong> 
                                        <a href="${result.raw_url}" target="_blank">${result.raw_url}</a>
                                    </p>
                                    <p><strong>Execute URL:</strong> 
                                        <a href="${result.execute_url}" target="_blank">${result.execute_url}</a>
                                    </p>
                                    ${result.is_private ? '<p style="color: red;">⚠️ This file is password protected</p>' : ''}
                                    
                                    <h4>Update this file:</h4>
                                    <input type="file" id="updateFile">
                                    ${result.is_private ? '<input type="password" id="updatePassword" placeholder="Password to update"><br>' : ''}
                                    <button onclick="updateFile('${result.file_id}')">Update File</button>
                                `;
                            } else {
                                document.getElementById('result').innerHTML = 
                                    `<p style="color: red;">Error: ${result.error}</p>`;
                            }
                        } catch (error) {
                            document.getElementById('result').innerHTML = 
                                `<p style="color: red;">Error: ${error.message}</p>`;
                        }
                    };
                    
                    reader.readAsText(file);
                }
                
                async function updateFile(fileId) {
                    const fileInput = document.getElementById('updateFile');
                    const passwordInput = document.getElementById('updatePassword');
                    
                    if (!fileInput.files[0]) {
                        alert('Please select a file');
                        return;
                    }
                    
                    const file = fileInput.files[0];
                    
                    if (!file.name.endsWith('.py')) {
                        alert('Only Python files (.py) are allowed');
                        return;
                    }
                    
                    const reader = new FileReader();
                    reader.onload = async function(e) {
                        const content = e.target.result;
                        const base64Content = btoa(content);
                        
                        const data = {
                            filename: file.name,
                            content: base64Content,
                            password: passwordInput ? passwordInput.value : ''
                        };
                        
                        try {
                            const response = await fetch(`/api/update?file_id=${fileId}`, {
                                method: 'POST',
                                body: JSON.stringify(data),
                                headers: {
                                    'Content-Type': 'application/json'
                                }
                            });
                            
                            const result = await response.json();
                            
                            if (response.ok) {
                                alert('File updated successfully!');
                            } else {
                                alert(`Error: ${result.error}`);
                            }
                        } catch (error) {
                            alert(`Error: ${error.message}`);
                        }
                    };
                    
                    reader.readAsText(file);
                }
            </script>
        </body>
        </html>
        '''
        self.wfile.write(html.encode())
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            filename = data.get('filename')
            content = data.get('content')
            is_private = data.get('is_private', False)
            password = data.get('password', '')
            
            if not filename or not content:
                self.send_error(400, 'Missing filename or content')
                return
            
            # Generate unique ID
            file_id = generate_file_id()
            save_filename = f"{file_id}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, save_filename)
            
            # Decode and save file
            file_content = base64.b64decode(content)
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Store metadata
            files_data = load_data()
            passwords_data = load_passwords()
            
            files_data[file_id] = {
                'original_name': filename,
                'saved_name': save_filename,
                'upload_time': datetime.now().isoformat(),
                'is_private': is_private,
                'has_password': bool(password and is_private)
            }
            
            if is_private and password:
                passwords_data[file_id] = hash_password(password)
            
            save_data(files_data)
            save_passwords(passwords_data)
            
            # Get base URL
            base_url = f"{self.headers.get('X-Forwarded-Proto', 'https')}://{self.headers.get('Host')}"
            
            response = {
                'file_id': file_id,
                'raw_url': f"{base_url}/api/raw?file_id={file_id}",
                'execute_url': f"{base_url}/api/execute?file_id={file_id}",
                'is_private': is_private,
                'message': 'File uploaded successfully'
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_error(500, f'Server error: {str(e)}')
