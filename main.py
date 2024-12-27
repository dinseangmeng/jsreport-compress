import zipfile
import json
import base64
import os
from pathlib import Path
import re

class JSReportExportConverter:
    def __init__(self, export_path):
        self.export_path = export_path
        self.temp_dir = Path('temp_extract')
        self.assets = {}
        self.debug = True

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

    def process_assets(self):
        assets_dir = self.temp_dir / 'assets'
        self.log(f"Processing assets from: {assets_dir}")
        
        if assets_dir.exists():
            for asset_file in assets_dir.glob('*.json'):
                with open(asset_file, 'r') as f:
                    asset_data = json.load(f)
                    asset_name = asset_data.get('name')
                    content = asset_data.get('content', '')
                    
                    if not asset_name:
                        continue

                    # Determine content type from filename
                    if asset_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        content_type = 'image'
                        mime_type = 'image/' + asset_name.lower().split('.')[-1]
                    elif asset_name.lower().endswith('.css'):
                        content_type = 'css'
                        content = self.decode_base64_if_needed(content)
                        mime_type = 'text/css'
                    else:
                        content_type = 'unknown'
                        mime_type = 'application/octet-stream'

                    self.assets[asset_name] = {
                        'content': content,
                        'type': content_type,
                        'mime_type': mime_type
                    }
                    
                    self.log(f"Added asset: {asset_name} ({content_type})")

    def replace_assets_in_content(self, content):
        """Replace asset placeholders with actual content."""
        for asset_name, asset_data in self.assets.items():
            if asset_data['type'] == 'css':
                # Handle CSS assets
                patterns = [
                    '{{ asset "' + asset_name + '" "utf8" }}',
                    "{{ asset '" + asset_name + "' 'utf8' }}"
                ]
                for pattern in patterns:
                    if pattern in content:
                        content = content.replace(pattern, asset_data['content'])
                
            elif asset_data['type'] == 'image':
                # Handle image assets - both in direct src and in asset tags
                self.log(f"Processing image asset: {asset_name}")
                patterns = [
                    '{{ asset "' + asset_name + '" "dataURI" }}',
                    "{{ asset '" + asset_name + "' 'dataURI' }}",
                    'src="{{asset \'' + asset_name + '\' \'dataURI\'}}"',
                    'src="{{asset "' + asset_name + '" "dataURI"}}"'
                ]
                data_uri = f"data:{asset_data['mime_type']};base64,{asset_data['content']}"
                
                for pattern in patterns:
                    if pattern in content:
                        self.log(f"Replacing pattern: {pattern}")
                        if pattern.startswith('src='):
                            # For src attributes, we need to keep the src=""
                            content = content.replace(pattern, f'src="{data_uri}"')
                        else:
                            content = content.replace(pattern, data_uri)

        return content

    def process_templates(self):
        templates_dir = self.temp_dir / 'templates'
        templates = []
        
        if templates_dir.exists():
            for template_file in templates_dir.glob('*.json'):
                self.log(f"Processing template file: {template_file}")
                with open(template_file, 'r') as f:
                    template_data = json.load(f)

                # Copy original template config
                template = template_data.copy()
                
                # Replace assets in content field if it exists
                if 'content' in template:
                    template['content'] = self.replace_assets_in_content(template['content'])
                
                templates.append(template)
                self.log(f"Added template: {template['name']}")

        return templates

    def convert(self):
        try:
            self.log("Starting conversion...")
            self.extract_export()
            self.process_assets()
            templates = self.process_templates()
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