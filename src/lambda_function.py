import json
import base64
import gzip
import urllib.request
import os
import boto3

def lambda_handler(event, context):
    api_key = os.environ.get('GEMINI_API_KEY')
    sns_arn = os.environ.get('SNS_TOPIC_ARN')

    cw_data = event['awslogs']['data']
    compressed_payload = base64.b64decode(cw_data)
    uncompressed_payload = gzip.decompress(compressed_payload)
    log_data = json.loads(uncompressed_payload)
    
    for log_event in log_data['logEvents']:
        raw_attack = json.loads(log_event['message'])
        
        attacker_ip = raw_attack.get('src_ip', 'Unknown')
        cmd = raw_attack.get('input', '')
        event_id = raw_attack.get('eventid', 'Unknown')

        if event_id == 'cowrie.command.input':
            print(f"🚨 ALERT: Command intercepted from {attacker_ip}: {cmd}")
            analyze_with_ai(cmd, attacker_ip, api_key, sns_arn)
            
    return {'statusCode': 200, 'body': json.dumps('Complete')}

def analyze_with_ai(command, ip, api_key, sns_arn):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"A hacker just typed this command into our Linux honeypot: '{command}'. Explain what this command does and their likely goal in under 3 sentences."
    
    data = {"contents": [{"parts":[{"text": prompt}]}]}
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    
    try:
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode('utf-8'))
        ai_analysis = result['candidates'][0]['content']['parts'][0]['text']
        
        # Build the final alert message
        alert_msg = f"🚨 HONEYPOT BREACH DETECTED 🚨\n\nAttacker IP: {ip}\nCommand: {command}\n\n🧠 AI INTELLIGENCE REPORT:\n{ai_analysis}"
        print(alert_msg)
        
        # Send to Email via SNS
        if sns_arn:
            sns = boto3.client('sns')
            sns.publish(TopicArn=sns_arn, Message=alert_msg, Subject="Honeypot AI Alert")
            print("✅ Email Alert Sent Successfully!")
            
    except Exception as e:
        print(f"⚠️ AI/SNS Failed: {str(e)}")
