import sys
import requests

def upload(file_path, signed_url):
    content_type = "image/jpeg" if file_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
    headers = {
        "Cache-Control": "public, max-age=31536000, immutable",
        "Content-Disposition": "inline",
        "Content-Type": content_type,
        "x-amz-acl": "public-read"
    }
    with open(file_path, 'rb') as f:
        data = f.read()
    
    resp = requests.put(signed_url, data=data, headers=headers)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Upload successful!")
    else:
        print(f"Error: {resp.text}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python upload_to_s3.py <file_path> <signed_url>")
        sys.exit(1)
    upload(sys.argv[1], sys.argv[2])
