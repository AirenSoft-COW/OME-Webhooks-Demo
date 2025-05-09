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
                    'fileName': 'passthrough',
                    'name': 'Passthrough',
                    'renditions': [
                        {
                            'name': 'bypass',
                            'audio': 'bypass_audio',
                            'video': 'bypass_video'
                        }
                    ]
                },
                {
                    'fileName': 'abr',
                    'name': 'ABR',
                    'renditions': [
                        {
                            'name': '1280p',
                            'audio': 'audio_aac',
                            'video': 'video_1280'
                        },
                        {
                            'name': '720p',
                            'audio': 'audio_aac',
                            'video': 'video_720'
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
                        'name': 'video_1280',
                        'codec': 'h264',
                        'width': 1920,
                        'height': 1080,
                        'bitrate': 5120000,
                        'framerate': 30,
                        'keyFrameInterval': 30,
                        'preset': 'faster',
                        'bFrames': 0
                    },
                    {
                        'name': 'video_720',
                        'codec': 'h264',
                        'width': 1280,
                        'height': 720,
                        'bitrate': 2024000,
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
