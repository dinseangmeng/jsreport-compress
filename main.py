import zipfile
import json
import base64
import os
from pathlib import Path
import re
import mimetypes

class JSReportExportConverter:
    def __init__(self, export_path):
        self.export_path = export_path
        self.temp_dir = Path('temp_extract')
        self.assets = {}
        self.debug = True
        # Initialize mimetypes
        mimetypes.init()

    def log(self, message):
        if self.debug:
            print(f"DEBUG: {message}")

    def extract_export(self):
        self.temp_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(self.export_path, 'r') as zip_ref:
            self.log(f"Files in export: {zip_ref.namelist()}")
            zip_ref.extractall(self.temp_dir)

    def decode_base64_if_needed(self, content):
        """Try to decode base64 content if it looks encoded."""
        try:
            # Check if it starts with a base64 pattern
            if re.match(r'^[A-Za-z0-9+/]*={0,2}$', content):
                return base64.b64decode(content).decode('utf-8')
            return content
        except:
            return content

    def get_mime_type(self, filename):
        """Determine MIME type from filename."""
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            extension = filename.lower().split('.')[-1] if '.' in filename else ''
            # Handle common types
            if extension in ['js']:
                return 'application/javascript'
            elif extension in ['css']:
                return 'text/css'
            elif extension in ['ttf']:
                return 'font/ttf'
            elif extension in ['woff']:
                return 'font/woff'
            elif extension in ['woff2']:
                return 'font/woff2'
            elif extension in ['eot']:
                return 'application/vnd.ms-fontobject'
            elif extension in ['svg']:
                return 'image/svg+xml'
            else:
                return 'application/octet-stream'
        return mime_type

    def process_assets(self):
        """Process all assets from the export."""
        # First, look for binary files directly
        self.log("Scanning for binary assets (fonts, images)...")
        for file_ext in ['.ttf', '.woff', '.woff2', '.eot', '.svg', '.png', '.jpg', '.jpeg', '.gif']:
            for asset_file in self.temp_dir.glob(f'**/*{file_ext}'):
                asset_name = asset_file.name
                try:
                    with open(asset_file, 'rb') as f:
                        content = base64.b64encode(f.read()).decode('utf-8')
                    
                    mime_type = self.get_mime_type(asset_name)
                    
                    self.assets[asset_name] = {
                        'content': content,
                        'mime_type': mime_type
                    }
                    
                    self.log(f"Added binary asset: {asset_name} ({mime_type})")
                except Exception as e:
                    self.log(f"Error processing binary asset {asset_file}: {e}")
        
        # Process JSON assets from the assets directory
        assets_dir = self.temp_dir / 'assets'
        self.log(f"Looking for JSON assets in: {assets_dir}")
        
        if assets_dir.exists():
            for asset_file in assets_dir.glob('**/*.json'):
                try:
                    self.log(f"Processing asset file: {asset_file}")
                    with open(asset_file, 'r', encoding='utf-8') as f:
                        asset_data = json.load(f)
                    
                    asset_name = asset_data.get('name')
                    content = asset_data.get('content', '')
                    
                    if not asset_name:
                        self.log(f"Skipping asset without name in {asset_file}")
                        continue

                    mime_type = self.get_mime_type(asset_name)
                    
                    # For CSS or JS, try to decode if needed
                    if asset_name.lower().endswith(('.css', '.js')):
                        content = self.decode_base64_if_needed(content)
                    
                    self.assets[asset_name] = {
                        'content': content,
                        'mime_type': mime_type
                    }
                    
                    self.log(f"Added JSON asset: {asset_name} ({mime_type})")
                except Exception as e:
                    self.log(f"Error processing JSON asset {asset_file}: {e}")
        
        # Process any text files (CSS, JS) directly
        for file_ext in ['.css', '.js']:
            for asset_file in self.temp_dir.glob(f'**/*{file_ext}'):
                asset_name = asset_file.name
                if asset_name not in self.assets:  # Don't process if already added
                    try:
                        with open(asset_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        mime_type = self.get_mime_type(asset_name)
                        
                        self.assets[asset_name] = {
                            'content': content,
                            'mime_type': mime_type
                        }
                        
                        self.log(f"Added text asset: {asset_name} ({mime_type})")
                    except Exception as e:
                        self.log(f"Error processing text asset {asset_file}: {e}")

    def replace_assets_in_content(self, content):
        """Replace asset placeholders with actual content."""
        # Handle standard asset syntax
        standard_pattern = r'{{\s*asset\s*[\'"]([^\'"]+)[\'"]\s*[\'"]([^\'"]+)[\'"]\s*}}'
        for match in re.finditer(standard_pattern, content):
            try:
                asset_name = match.group(1)
                asset_type = match.group(2)
                
                if asset_name in self.assets:
                    asset_data = self.assets[asset_name]
                    replacement = ""
                    
                    if asset_type == "utf8":
                        replacement = asset_data['content']
                    elif asset_type == "dataURI":
                        replacement = f"data:{asset_data['mime_type']};base64,{asset_data['content']}"
                    
                    content = content.replace(match.group(0), replacement)
                    self.log(f"Replaced standard asset: {asset_name}")
            except Exception as e:
                self.log(f"Error replacing standard asset: {e}")
        
        # Handle alternate asset syntax for fonts and other assets
        alt_pattern = r'{#asset\s+([^\s@]+)\s+@encoding=(\w+)}'
        for match in re.finditer(alt_pattern, content):
            try:
                asset_name = match.group(1)
                encoding_type = match.group(2)
                
                self.log(f"Found alternate asset reference: {asset_name} with encoding {encoding_type}")
                
                if asset_name in self.assets:
                    asset_data = self.assets[asset_name]
                    
                    if encoding_type.lower() == "datauri":
                        replacement = f"data:{asset_data['mime_type']};base64,{asset_data['content']}"
                        content = content.replace(match.group(0), replacement)
                        self.log(f"Replaced alternate asset: {asset_name}")
                else:
                    self.log(f"Asset not found: {asset_name}")
            except Exception as e:
                self.log(f"Error replacing alternate asset: {e}")
        
        # Handle src attributes with asset references
        src_pattern = r'src\s*=\s*[\'"]{{asset\s*[\'"]([^\'"]+)[\'"]\s*[\'"]([^\'"]+)[\'"]}}[\'"]'
        for match in re.finditer(src_pattern, content):
            try:
                asset_name = match.group(1)
                asset_type = match.group(2)
                
                if asset_name in self.assets and asset_type == "dataURI":
                    asset_data = self.assets[asset_name]
                    data_uri = f"data:{asset_data['mime_type']};base64,{asset_data['content']}"
                    replacement = f'src="{data_uri}"'
                    content = content.replace(match.group(0), replacement)
                    self.log(f"Replaced src asset: {asset_name}")
            except Exception as e:
                self.log(f"Error replacing src asset: {e}")
        
        # Handle url() with alternate asset syntax
        url_alt_pattern = r'url\s*\(\s*{#asset\s+([^\s@]+)\s+@encoding=(\w+)}\s*\)'
        for match in re.finditer(url_alt_pattern, content):
            try:
                asset_name = match.group(1)
                encoding_type = match.group(2)
                
                if asset_name in self.assets and encoding_type.lower() == "datauri":
                    asset_data = self.assets[asset_name]
                    data_uri = f"data:{asset_data['mime_type']};base64,{asset_data['content']}"
                    replacement = f'url("{data_uri}")'
                    content = content.replace(match.group(0), replacement)
                    self.log(f"Replaced url alt asset: {asset_name}")
            except Exception as e:
                self.log(f"Error replacing url alt asset: {e}")
        
        # Handle regular url() patterns
        url_pattern = r'url\s*\(\s*[\'"]?([^\'"\(\)]+)[\'"]?\s*\)'
        for match in re.finditer(url_pattern, content):
            url = match.group(1)
            if url.startswith('data:'):  # Already a data URI
                continue
                
            asset_name = url.split('/')[-1]  # Get the filename from URL
            if asset_name in self.assets:
                asset_data = self.assets[asset_name]
                data_uri = f"data:{asset_data['mime_type']};base64,{asset_data['content']}"
                replacement = f'url("{data_uri}")'
                content = content.replace(match.group(0), replacement)
                self.log(f"Replaced CSS url: {asset_name}")
        
        return content

    def process_templates(self):
        templates = []
        templates_dir = self.temp_dir / 'templates'
        
        if templates_dir.exists():
            for template_file in templates_dir.glob('**/*.json'):
                try:
                    self.log(f"Processing template file: {template_file}")
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    # Copy original template config
                    template = template_data.copy()
                    
                    # Process content if it exists
                    if 'content' in template:
                        template['content'] = self.replace_assets_in_content(template['content'])
                    
                    templates.append(template)
                    self.log(f"Added template: {template.get('name', 'unnamed')}")
                except Exception as e:
                    self.log(f"Error processing template {template_file}: {e}")
        else:
            # If no templates directory, look for template files in the root
            for template_file in self.temp_dir.glob('*.json'):
                if template_file.name != 'export.json':  # Skip export metadata
                    try:
                        self.log(f"Processing root template file: {template_file}")
                        with open(template_file, 'r', encoding='utf-8') as f:
                            template_data = json.load(f)
                        
                        if isinstance(template_data, dict) and 'content' in template_data:
                            template = template_data.copy()
                            template['content'] = self.replace_assets_in_content(template['content'])
                            templates.append(template)
                            self.log(f"Added root template: {template.get('name', 'unnamed')}")
                    except Exception as e:
                        self.log(f"Error processing root template {template_file}: {e}")
        
        return templates

    def convert(self):
        try:
            self.log("Starting conversion...")
            self.extract_export()
            self.process_assets()
            templates = self.process_templates()
            
            if not templates:
                self.log("WARNING: No templates found in the export!")
            
            self.log("Conversion completed.")
            return templates
        finally:
            # Cleanup
            import shutil
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)

    def save(self, output_path):
        templates = self.convert()
        
        # Create output directory if it doesn't exist
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save templates
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=2, ensure_ascii=False)
        self.log(f"Saved {len(templates)} templates to {output_path}")
        return templates

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python script.py <export_file.jsrexport> <output.json>")
        sys.exit(1)

    export_file = sys.argv[1]
    output_file = sys.argv[2]
    
    converter = JSReportExportConverter(export_file)
    converter.save(output_file)