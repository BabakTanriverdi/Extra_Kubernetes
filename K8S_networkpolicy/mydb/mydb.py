from flask import Flask

app = Flask(__name__)

@app.route('/')
def main():
    return '''<!DOCTYPE html>
<html>
<head>
    <title>My DB</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            min-height: 100vh;
            display: flex; align-items: center; justify-content: center;
            background: #0a0a0a;
            font-family: 'Courier New', monospace;
            color: #0f0;
        }
        .terminal {
            width: 650px;
            background: #111;
            border-radius: 12px;
            border: 1px solid #333;
            overflow: hidden;
            box-shadow: 0 0 40px rgba(0,255,0,0.05);
        }
        .topbar {
            background: #222;
            padding: 10px 16px;
            display: flex; align-items: center; gap: 8px;
        }
        .dot { width: 12px; height: 12px; border-radius: 50%; }
        .red { background: #ff5f56; }
        .yellow { background: #ffbd2e; }
        .green { background: #27c93f; }
        .topbar span { color: #888; font-size: 13px; margin-left: 10px; }
        .body { padding: 24px; font-size: 14px; line-height: 1.8; }
        .prompt { color: #0f0; }
        .cmd { color: #fff; }
        .dim { color: #555; }
        .info { color: #0af; }
        .warn { color: #ffbd2e; }
        table { width: 100%; margin: 12px 0; border-collapse: collapse; }
        th { color: #0af; text-align: left; border-bottom: 1px solid #333; padding: 6px 10px; }
        td { color: #ccc; padding: 6px 10px; border-bottom: 1px solid #1a1a1a; }
        .cursor { animation: blink 1s infinite; }
        @keyframes blink { 0%,50% { opacity: 1; } 51%,100% { opacity: 0; } }
        .badge { display: inline-block; margin-top: 16px; padding: 4px 12px; border: 1px solid #0f0; border-radius: 4px; font-size: 12px; color: #0f0; }
    </style>
</head>
<body>
    <div class="terminal">
        <div class="topbar">
            <div class="dot red"></div>
            <div class="dot yellow"></div>
            <div class="dot green"></div>
            <span>babak@mydb ~ </span>
        </div>
        <div class="body">
            <div><span class="prompt">$</span> <span class="cmd">mysql -u babak -p mydb</span></div>
            <div class="dim">Connecting to database...</div>
            <div class="info">Connected to MyDB v1.0 &#10003;</div>
            <br>
            <div><span class="prompt">mysql&gt;</span> <span class="cmd">SHOW TABLES;</span></div>
            <table>
                <tr><th>Table</th><th>Rows</th><th>Status</th></tr>
                <tr><td>users</td><td>1,204</td><td style="color:#27c93f;">&#9679; active</td></tr>
                <tr><td>orders</td><td>8,439</td><td style="color:#27c93f;">&#9679; active</td></tr>
                <tr><td>products</td><td>352</td><td style="color:#27c93f;">&#9679; active</td></tr>
                <tr><td>sessions</td><td>47</td><td style="color:#ffbd2e;">&#9679; idle</td></tr>
            </table>
            <div><span class="dim">4 tables in set (0.003 sec)</span></div>
            <br>
            <div><span class="prompt">mysql&gt;</span> <span class="cmd">SELECT VERSION();</span></div>
            <div class="info">MyDB v1.0 | K8s Pod | Built by Babak</div>
            <br>
            <div><span class="prompt">mysql&gt;</span> <span class="cursor">_</span></div>
            <div class="badge">&#9881; Deployed with Kubernetes + Helm</div>
        </div>
    </div>
</body>
</html>'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)