from flask import Flask, render_template, request, make_response
from flask_socketio import SocketIO, emit
import logging
from logging.handlers import RotatingFileHandler
import os
import requests
import base64
import hmac
import hashlib
import json
import threading
import time
from urllib.parse import quote

from data import OutputProfiles

app = Flask(__name__)
app.config.from_pyfile('conf/config.cfg')

os.makedirs(os.path.join(os.path.dirname(__file__), 'logs'), exist_ok=True)
log_file = os.path.join(os.path.dirname(__file__),
                        'logs', 'control-server.log')

file_handler = RotatingFileHandler(
    log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

socketio = SocketIO(app, cors_allowed_origins="*", async_handlers=True)

INGRESS_OME = app.config['INGRESS_OME']
ORIGIN_OME = app.config['ORIGIN_OME']


def get_req_resp_info(r):
    return {
        'headers': dict(r.headers),
        'body': r.get_json(silent=True)
    }


def emit_log(message, payload):
    payload = {
        'title': message,
        'payload': payload,
    }
    socketio.emit('log', payload)


def verify_signature(signature, payload, secret_key):

    message = 'Success'

    if signature is None:
        message = 'Missing X-OME-Signature header.'
        return False, message

    # Calculate HMAC-SHA1 using the secret key
    hmac_digest = hmac.new(secret_key.encode(
        'utf-8'), payload.encode('utf-8'), hashlib.sha1).digest()

    # Encode the HMAC digest in Base64 URL Safe format
    calculated_signature = base64.urlsafe_b64encode(
        hmac_digest).decode('utf-8').rstrip('=')

    # Compare the calculated signature with the provided signature
    if hmac.compare_digest(calculated_signature, signature):
        return True, message
    else:
        message = 'Invalid X-OME-Signature header.'
        return False, message


def get_ome_auth_header(token):
    return {
        'authorization': f'Basic {base64.b64encode(token.encode("utf-8")).decode("utf-8")}'
    }


def get_request_url(host, path):
    """
    Get the request URL for the given host and path.
    """
    return f'http://{host["host"]}:{host["api_port"]}{path}'


def request_get(host, path):

    url = get_request_url(host, path)
    headers = get_ome_auth_header(host['access_token'])

    app.logger.info(f'GET request URL: {url}')
    app.logger.info(f'GET request headers: {headers}')
    app.logger.info(f'GET request path: {path}')

    response = requests.get(url, headers=headers)
    return response


def request_post(host, path, data, message=None):

    url = get_request_url(host, path)
    headers = get_ome_auth_header(host['access_token'])

    log_message = ''

    if message is not None:
        log_message = f'{message} '

    emit_log(f'[REQUEST] {log_message}POST {url}', {
        'headers': headers,
        'body': data
    })

    app.logger.info(f'POST request URL: {url}')
    app.logger.info(f'POST request headers: {headers}')
    app.logger.info(f'POST request path: {path}')
    app.logger.info(f'POST request data:\n{json.dumps(data, indent=2)}')

    response = requests.post(url, headers=headers, json=data)

    emit_log(f'[RESPONSE] {log_message}({response.status_code}) ', {
        'headers': dict(response.headers),
        'body': response.json()
    })

    return response


def start_push_stream(ingress_ome, ingress_stream_name, origin_ome, origin_stream_name):
    """
    Using Push Publishing API to push the stream to the Origin OME.
    #start-push-publishing
    Reference: https://docs.ovenmediaengine.com/rest-api/v1/virtualhost/application/push
    """
    try:
        app.logger.info(
            f'Start push stream request from Ingress OME({ingress_ome["host"]}) to Origin OME({origin_ome["host"]}).')

        # RTMP Push
        # data = {
        #     # Simply we generate a UUID with the prefix push_ for 'id' field.
        #     'id': f'push_{ingress_stream_name}',
        #     'stream': {
        #         'name': ingress_stream_name
        #     },
        #     'protocol': 'rtmp',
        #     'url': f'rtmp://{origin_ome["host"]}:{origin_ome["rtmp_ingress_port"]}/{origin_ome["app_name"]}',
        #     'streamKey': origin_stream_name,
        # }

        # SRT Push
        stream_id = f'srt://{origin_ome["host"]}:{origin_ome["srt_ingress_port"]}/{origin_ome["app_name"]}/{origin_stream_name}'
        data = {
            # Simply we generate a UUID with the prefix push_ for 'id' field.
            'id': f'push_{ingress_stream_name}',
            'stream': {
                'name': ingress_stream_name
            },
            'protocol': 'srt',
            'url': f'srt://{origin_ome["host"]}:{origin_ome["srt_ingress_port"]}?streamid={quote(stream_id)}',
        }

        push_api_url = f'/v1/vhosts/{ingress_ome["vhost_name"]}/apps/{ingress_ome["app_name"]}:startPush'

        response = request_post(ingress_ome, push_api_url, data)

        if response.status_code == 200:

            app.logger.info(
                f'Push stream request success. Response:\n{json.dumps(response.json(), indent=2)}')
            return (True, 'success')
        else:

            app.logger.error(
                f'Push stream request request failed. Response:\n{response.status_code}\n{json.dumps(response.json(), indent=2)}')
            return (False, response.json().get('message', 'Unknown error'))

    except Exception as e:
        app.logger.error(f'Push stream request failed: {e}')
        return (False, f'Error occurred while processing the request {e}')


def stop_push_stream(ingress_ome, ingress_stream_name):
    """
    Using Push Publishing API to stop the stream to the Origin OME.
    """
    try:

        app.logger.info(
            f'Stop push stream request to Ingress OME({ingress_ome["host"]}).')

        data = {
            'id': f'push_{ingress_stream_name}'
        }

        push_api_url = f'/v1/vhosts/{ingress_ome["vhost_name"]}/apps/{ingress_ome["app_name"]}:stopPush'

        response = request_post(ingress_ome, push_api_url, data)

        if response.status_code == 200:
            app.logger.info(
                f'Stop push stream request success. Response:\n{json.dumps(response.json(), indent=2)}')
            return (True, 'success')
        else:
            app.logger.error(
                f'Stop push stream request failed. Response:\n{response.status_code}\n{json.dumps(response.json(), indent=2)}')
            return (False, response.json().get('message', 'Unknown error'))

    except Exception as e:
        app.logger.error(f'Stop push stream request failed: {e}')
        return (False, f'Error occurred while processing the request {e}')


def create_pull_stream(ingress_ome, ingress_stream_name, origin_ome, pull_stream_name):
    """
    Create a pull stream on the Origin OME to retrieve the stream from the Ingress OME via OVT.
    Reference: https://docs.ovenmediaengine.com/rest-api/v1/virtualhost/application/stream#create-stream-pull
    """
    try:
        app.logger.info(
            f'Create a pull stream on Origin OME({origin_ome["host"]}) to retrieve the stream from Ingress OME({ingress_ome["host"]}).')

        data = {
            'name': pull_stream_name,
            'urls': [
                f'ovt://{ingress_ome["host"]}:{ingress_ome["ovt_publisher_port"]}/{ingress_ome["app_name"]}/{ingress_stream_name}'
            ],
            "properties": {
                'persistent': True,
                'ignoreRtcpSRTimestamp': False
            }
        }

        create_stream_api_url = f'/v1/vhosts/{origin_ome["vhost_name"]}/apps/{origin_ome["app_name"]}/streams'

        response = request_post(
            origin_ome, create_stream_api_url, data, 'Create pull stream')

        if response.status_code == 200:
            app.logger.info(
                f'Create a pull stream request success. Response:\n{json.dumps(response.json(), indent=2)}')
            return (True, 'success')
        else:
            app.logger.error(
                f'Create a pull stream request failed. Response:\n{response.status_code}\n{json.dumps(response.json(), indent=2)}')
            return (False, response.json().get('message', 'Unknown error'))

    except Exception as e:
        app.logger.error(f'Create a pull stream request failed: {e}')
        return (False, f'Error occurred while processing the request {e}')


def delayed_create_pull_stream(ingress_ome, ingress_stream_name, origin_ome, pull_stream_name, delay):
    """
    Delays the execution of create_pull_stream by the specified number of seconds.
    """
    time.sleep(delay)  # Delay execution
    create_pull_stream(ingress_ome, ingress_stream_name,
                       origin_ome, pull_stream_name)


@app.route('/')
def index():
    """
    router for serving demo web page
    """

    return render_template('index.html')


@app.route('/redoc')
def redoc():

    return render_template('redoc.html')


@app.route('/swagger')
def swagger():

    return render_template('swagger.html')


@app.route('/rapidoc')
def rapidoc():

    return render_template('rapidoc.html')


@app.route('/v1/admission_webhooks', methods=['POST'])
def admission_webhooks():
    """
    Admission webhook for Ingress OME.
    Reference: https://docs.ovenmediaengine.com/access-control/admission-webhooks

    It is called when a new RTMP ingress is opened or closed on the Ingress OME,
    as configured in Ingress OME.

    In the Server.xml file of the Ingress OME,

    <AdmissionWebhooks>
        <ControlServerUrl>http://control-server:5000/v1/admission_webhooks</ControlServerUrl>
        <SecretKey>1234</SecretKey>
        <Timeout>3000</Timeout>
        <Enables>
            <Providers>rtmp</Providers>
        </Enables>
    </AdmissionWebhooks>

    Since we have only configured RTMP in the <Enables><Provider> section,
    OME calls the admission webhook only when an RTMP input is opened.
    """

    emit_log('Admission Webhooks request from Ingress OME',
             get_req_resp_info(request))

    header = request.headers
    app.logger.info(f'Admission webhook received header:\n {header}')

    """
    The X-Ome-Signature header is used to verify the signature of the request.
    """
    signature = header.get('X-Ome-Signature')
    payload = request.get_data(as_text=True)

    verifying_signature_succeed, message = verify_signature(
        signature, payload, INGRESS_OME['admission_webhook_secret_key'])

    if not verifying_signature_succeed:
        app.logger.error(
            f'Admission webhook signature verification failed: {message}')
        return {'allowed': False, 'message': message}
    else:
        app.logger.info(
            f'Admission webhook signature verification succeeded')

    data = request.get_json()
    app.logger.info(
        f'Admission webhook received data:\n{json.dumps(data, indent=2)}')

    """
    Handle the admission webhook request from the Ingress OME.
    Reference: https://docs.ovenmediaengine.com/access-control/admission-webhooks#request
    """
    if data['request']['status'] == 'opening':

        """
        At this point, we can add logic to determine the Origin OME
        which this RTMP stream should be pushed, based on the URL or stream name.
        We can also return {'allowed': false} to reject the stream input.

        response-for-opening-status:
        #response-for-opening-status
        Reference: https://docs.ovenmediaengine.com/access-control/admission-webhooks
        """

        stream_name = data['request']['url'].split('/')[-1]

        """
        We will simply reuse the ingress stream name for either a push or pull stream.
        """

        # For a push stream
        #
        # succeed, message = start_push_stream(INGRESS_OME, stream_name,
        #                                      ORIGIN_OME, stream_name)

        # if succeed:
        #     """
        #     In the demo, we simply set allow to true if the push is successful,
        #     allowing the input stream.
        #     This behavior may change depending on the architecture decision.
        #     """
        #     return {'allowed': True}
        # else:
        #     """
        #     Handle some error cases here.
        #     """
        #     return {
        #         'allowed': False,
        #         'reason': message
        #     }

        # For a pull stream
        """
        NOTE:
        Since the stream is not created on the Ingress OME during the admission webhook stage, 
        the Origin OME fails to pull the stream.
        The structure for this part is still under discussion and will be finalized later.
        
        In the demo, we temporarily return {allowed: true} from the admission webhook to allow the Ingress stream to be created.
        Then, we delay the pull stream creation request by 3 seconds.
        """
        threading.Thread(target=delayed_create_pull_stream, args=(
            INGRESS_OME, stream_name, ORIGIN_OME, stream_name, 3)).start()

        response = make_response({
            'allowed': True,
        })

        emit_log('Admission Webhooks response to Ingress OME',
                 get_req_resp_info(response))

        return response

    else:
        """
        handle data['request']['status'] == 'closing':
        """

        """
        response-for-closing-status
        #response-for-closing-status
        Reference: https://docs.ovenmediaengine.com/access-control/admission-webhooks
        """

        response = make_response({})
        emit_log('[RESPONSE] Admission Webhooks response to OME',
                 get_req_resp_info(response))

        return response


@app.route('/v1/transcode_webhook', methods=['POST'])
def transcode_webhook():
    """
    Transcode webhook for Origin OME.
    Reference: https://docs.ovenmediaengine.com/transcoding/transcodewebhook
    """

    emit_log('Transcode webhook request from Origin OME',
             get_req_resp_info(request))

    header = request.headers
    app.logger.info(f'Transcode webhook received header:\n {header}')

    signature = header.get('X-Ome-Signature')
    payload = request.get_data(as_text=True)

    verifying_signature_succeed, message = verify_signature(
        signature, payload, ORIGIN_OME['transcode_webhook_secret_key'])

    if not verifying_signature_succeed:
        app.logger.error(
            f'Transcode webhook signature verification failed: {message}')
        return {'allowed': False, 'message': message}
    else:
        app.logger.info(
            f'Transcode webhook signature verification succeeded')

    data = request.get_json()
    app.logger.info(
        f'Transcode webhook received data:\n{json.dumps(data, indent=2)}')

    """
    Handle the transcode webhook request from the Origin OME.
    Reference: https://docs.ovenmediaengine.com/transcoding/transcodewebhook#request-ome-control-server
    """

    """
    We can use the Transcode WebHook request information sent by the Origin OME 
    to control how the stream will be encoded.

    {
        "source": "TCP://172.18.0.1:40954",
        "stream": {
            "name": "stream",
            "virtualHost": "default"
            "application": "app",
            "sourceType": "Rtmp",
            "sourceUrl": "TCP://172.18.0.1:40954",
            "tracks": [...],
            "createdTime": "2025-05-09T11:51:44.389+00:00",
        }
    }
    """

    """
    There are no encoding settings in the <OutputProfiles> section of the Origin OME's Server.xml.
    We can inject ABR encoding settings using the transcoding webhook.
    """

    output_profiles = OutputProfiles.HIGH_RES_ABR

    response = make_response({
        'allowed': True,
        'outputProfiles': output_profiles,
    })

    emit_log('Transcode webhook response to Origin OME',
             get_req_resp_info(response))

    return response


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(5000),
                 debug=True, use_reloader=True, allow_unsafe_werkzeug=True)
