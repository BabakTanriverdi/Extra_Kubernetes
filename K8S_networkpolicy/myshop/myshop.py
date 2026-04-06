from flask import Flask

app = Flask(__name__)

@app.route('/')
def storefront():
    return '''<!DOCTYPE html>
<html>
<head>
    <title>My Shop</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            min-height: 100vh;
            display: flex; align-items: center; justify-content: center;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #fff;
        }
        .container {
            text-align: center;
            padding: 60px 40px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            max-width: 700px;
        }
        .logos {
            display: flex; justify-content: center; gap: 30px;
            margin-bottom: 30px;
        }
        .logos img { height: 70px; filter: drop-shadow(0 0 12px rgba(50,140,255,0.4)); }
        h1 {
            font-size: 2.8rem;
            background: linear-gradient(90deg, #326ce5, #0dd3ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 15px;
        }
        p { font-size: 1.1rem; color: #aab; line-height: 1.6; }
        .badge {
            display: inline-block;
            margin-top: 25px;
            padding: 10px 28px;
            border-radius: 30px;
            background: linear-gradient(90deg, #326ce5, #0dd3ff);
            color: #fff;
            font-weight: 600;
            font-size: 0.95rem;
            letter-spacing: 0.5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logos">
            <img src="https://raw.githubusercontent.com/kubernetes/kubernetes/master/logo/logo.svg" alt="Kubernetes">
            <img src="https://helm.sh/img/helm.svg" alt="Helm">
        </div>
        <h1>WELCOME TO MY SHOP</h1>
        <p>Deployed with Kubernetes &amp; Helm<br>Built by Babak</p>
        <div class="badge">&#9781; Powered by K8s + Helm</div>
    </div>
</body>
</html>'''

@app.route('/account')
def account():
    return '<h1 style="text-align:center;margin-top:50px;color:#326ce5;">Account Page - Coming Soon</h1>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
