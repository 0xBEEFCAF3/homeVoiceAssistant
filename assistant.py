#!/usr/bin/env python3
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run a recognizer using the Google Assistant Library with button support.

The Google Assistant Library has direct access to the audio API, so this Python
code doesn't need to record audio. Hot word detection "OK, Google" is supported.

It is available for Raspberry Pi 2/3 only; Pi Zero is not supported.
"""

import logging
import platform
import sys
import threading
import requests
import subprocess
import signal
import argparse
import locale
import requests
import mod.snowboydecoder as snowboydecoder

from google.assistant.library.event import EventType

from aiy.assistant import auth_helpers
from aiy.assistant.library import Assistant
from aiy.board import Board, Led
from aiy.voice import tts


class MyAssistant:
    """An assistant that runs in the background.

    The Google Assistant Library event loop blocks the running thread entirely.
    To support the button trigger, we need to run the event loop in a separate
    thread. Otherwise, the on_button_pressed() method will never get a chance to
    be invoked.
    """

    def __init__(self):
        self._task = threading.Thread(target=self._task_func)
        self._can_start_conversation = False
        self._assistant = None
        self._board = Board()
        self._board.button.when_pressed = self._on_button_pressed

    def _task_func(self):
        """Starts the assistant.

        Starts the assistant event loop and begin processing events.
        """
        for event in self._assistant.start(): 
            self._process_event(event)

    def config(self):
        credentials = auth_helpers.get_assistant_credentials()
        a = Assistant(credentials)
        self._assistant = a
        self._can_start_conversation = True
        self._task.start()
        print("configed")

    def power_off_pi():
        tts.say('Good bye!')
        subprocess.call('sudo shutdown now', shell=True)


    def reboot_pi():
        tts.say('See you in a bit!')
        subprocess.call('sudo reboot', shell=True)


    def say_ip():
        ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
        tts.say('My IP address is %s' % ip_address.decode('utf-8'))


    def _process_event(self, event):
        logging.info(event)
        if event.type == EventType.ON_START_FINISHED:
            self._board.led.status = Led.BEACON_DARK  # Ready.
            self._can_start_conversation = True
            # Start the voicehat button trigger.
            logging.info('Say "OK, Google" or press the button, then speak. '
                         'Press Ctrl+C to quit...')
        
        elif event.type == EventType.ON_CONVERSATION_TURN_STARTED:
            subprocess.call('aplay assets/ds9_beep_1.wav', shell=True)
            self._can_start_conversation = False
            self._board.led.state = Led.ON  # Listening.

        elif event.type == EventType.ON_END_OF_UTTERANCE:
            self._board.led.state = Led.PULSE_QUICK  # Thinking.
        elif event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
            print('You said:', event.args['text'])
            text = event.args['text'].lower()
            if text == 'power off':
                self._assistant.stop_conversation()
                self.power_off_pi()
            elif text == 'reboot':
                self._assistant.stop_conversation()
                self.reboot_pi()
            elif text == 'ip address':
                self._assistant.stop_conversation()
                self.say_ip()
            elif text == 'turn on my lights':
                self._assistant.stop_conversation()
                requests.get("http://192.168.0.3:5000/on")
            elif text == 'turn off my lights':
                self._assistant.stop_conversation()
                requests.get("http://192.168.0.3:5000/off")
            elif text == 'vibe my lights':
                self._assistant.stop_conversation()
                requests.get("http://192.168.0.3:5000/rainbow")
 
            
        elif (event.type == EventType.ON_CONVERSATION_TURN_FINISHED
              or event.type == EventType.ON_CONVERSATION_TURN_TIMEOUT
              or event.type == EventType.ON_NO_RESPONSE):
            self._board.led.state = Led.BEACON_DARK  # Ready.
            self._can_start_conversation = True

        elif event.type == EventType.ON_ASSISTANT_ERROR and event.args and event.args['is_fatal']:
            sys.exit(1)

    def _start_convo(self):
         # Check if we can start a conversation. 'self._can_start_conversation'
        # is False when either:
        # 1. The assistant library is not yet ready; OR
        # 2. The assistant library is already in a conversation.
        logging.info("STARTING CONVO")
        logging.info(self._can_start_conversation)
        if self._can_start_conversation:
            self._assistant.start_conversation()

    def _on_button_pressed(self):
       self._start_convo()

def volume(string):
    value = int(string)
    if value < 0 or value > 100:
        raise argparse.ArgumentTypeError('Volume must be in [0...100] range.')
    return value

def locale_language():
    language, _ = locale.getdefaultlocale()
    return language


def main():
    logging.basicConfig(level=logging.DEBUG)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))

    parser = argparse.ArgumentParser(description='Assistant service example.')
    parser.add_argument('--language', default=locale_language())
    parser.add_argument('--volume', type=volume, default=100)
    parser.add_argument('--model', default='./assets/Computer.pdml')
    args = parser.parse_args()

    detector = snowboydecoder.HotwordDetector(args.model, sensitivity=0.5)
    assistant = MyAssistant() 
    assistant.config()

    while True:
        logging.info('Speak own hotword and speak')
        detector.start()
        logging.info('Conversation started!')
        assistant._start_convo()     
if __name__ == '__main__':
    main()
