HIGH_RES_ABR = {
    'hwaccels': {
        'decoder': {
            'enable': False
        },
        'encoder': {
            'enable': False
        }
    },
    'outputProfile': [
        {
            'name': 'output_stream',
            'outputStreamName': '${OriginStreamName}',
            'playlists': [
                {
                    'fileName': 'abr',
                    'name': 'ABR',
                    'renditions': [
                        {
                            'name': '720p',
                            'audio': 'audio_aac',
                            'video': 'video_720p'
                        },
                        {
                            'name': '480p',
                            'audio': 'audio_aac',
                            'video': 'video_480p'
                        }
                    ]
                }
            ],
            'encodes': {
                'audios': [
                    {
                        'name': 'bypass_audio',
                        'bypass': True
                    },
                    {
                        'name': 'audio_aac',
                        'channel': 2,
                        'codec': 'aac',
                        'bitrate': 128000,
                        'samplerate': 48000,
                        'bypassIfMatch': {
                            'channel': 'eq',
                            'codec': 'eq',
                            'samplerate': 'lte'
                        }
                    }
                ],
                'videos': [
                    {
                        'name': 'bypass_video',
                        'bypass': True
                    },
                    {
                        'name': 'video_720p',
                        'codec': 'h264',
                        'width': 1280,
                        'height': 720,
                        'bitrate': 2048000,
                        'framerate': 30,
                        'keyFrameInterval': 30,
                        'preset': 'faster',
                        'bFrames': 0
                    },
                    {
                        'name': 'video_480p',
                        'codec': 'h264',
                        'width': 854,
                        'height': 480,
                        'bitrate': 1024000,
                        'framerate': 30,
                        'keyFrameInterval': 30,
                        'preset': 'faster',
                        'bFrames': 0
                    }
                ]
            }
        }
    ]
}
