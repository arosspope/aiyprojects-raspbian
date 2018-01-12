#!/usr/bin/env python3
# Copyright 2017 Andrew Pope.
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

"""A Google Assistant with some extra custom commands."""

import logging
import subprocess
import sys
import threading

from os import listdir
from os.path import isfile, join, splitext

import aiy.assistant.grpc
import aiy.audio
import aiy.voicehat

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
)   
    
def power_off_pi():
    aiy.audio.say('Good bye!')
    subprocess.call('sudo shutdown now', shell=True)

def reboot_pi():
    aiy.audio.say('See you in a bit!')
    subprocess.call('sudo reboot', shell=True)

def say_ip():
    ip_address = subprocess.check_output("hostname -I | cut -d' ' -f1", shell=True)
    aiy.audio.say('My IP address is %s' % ip_address.decode('utf-8'))
    
playshell = None
def play_track(text, button):
    track = text.lower().replace('play track', '', 1).strip()
    logging.info("playing track: %s", track)
    aiy.audio.say('Playing track %s' % track)
    
    global playshell
    if playshell == None:
        playshell = subprocess.Popen(["/usr/local/bin/mpsyt",""],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    
    playshell.stdin.write(bytes('/' + track + '\n1\n', 'utf-8'))
    playshell.stdin.flush()
    
    button.wait_for_press()
    pkill = subprocess.Popen(["/usr/bin/pkill", "vlc"],stdin=subprocess.PIPE)
    
def set_mood(button):
    aiy.audio.say('Time to light some candles')
    subprocess.call("mpc clear; mpc add http://77.235.42.90:80/; mpc play", shell=True)
    button.wait_for_press() # Assistant blocked while streaming
    pkill = subprocess.call("mpc stop", shell=True)

def list_stories():
    aiy.audio.say('The available stories include')
    stories = [f for f in listdir('stories') if isfile(join('stories', f))]
    for s in stories:
        aiy.audio.say('%s' % splitext(s)[0])

def tell_story(text):
    story = text.lower().replace('tell story', '', 1).strip().replace(" ", "-")
    stories = [f for f in listdir('stories') if isfile(join('stories', f))] # Get available stories
    stories = [splitext(x)[0] for x in stories] # Remove the '.txt'
    
    logging.info('searching for: %s' % story)
    stop_story = False
    if story not in stories:
        logging.warning('story not found')
        aiy.audio.say('Sorry, I dont know that one')
        list_stories()
    else:
        # For better or worse, the story will play out until finished
        # TODO: Adopt a multi-threaded approach, where a seperate thread watches for a button press
        with open('stories/%s.txt' % story, 'r') as f:
            for l in f.readlines():
                aiy.audio.say(l)

def process_event(assistant, status_ui, button):
    text, audio = assistant.recognize()
    if text:
        if text.lower() == 'shut down':
            #assistant.stop_conversation()
            power_off_pi()
            status_ui.status('power-off')
            logging.info('shuting down...')
            return
        elif text.lower() == 'reboot':
            #assistant.stop_conversation()
            reboot_pi()
            status_ui.status('power-off')
            logging.info('rebooting...')
            return
        elif text.lower() == 'ip address':
            # We allow athena to also play audio from the google assistant,
            # as that will give us our public ip
            say_ip()
        elif text.lower().startswith('play track'):
            play_track(text, button)
            return
        elif text.lower() == 'set the mood':
            set_mood(button)
            return
        elif text.lower() == 'list stories':
            list_stories()
            return
        elif text.lower().startswith('tell story'):
            tell_story(text)
            return
    
    if audio:
        aiy.audio.play_audio(audio)
    
    status_ui.status('error')
    logging.error('unknown command: %s' % text)
    

def main():
    status_ui = aiy.voicehat.get_status_ui()
    status_ui.status('starting')
    assistant = aiy.assistant.grpc.get_assistant()
    button = aiy.voicehat.get_button()
    
    with aiy.audio.get_recorder():
        while True:
            status_ui.status('ready')
            logging.info('Press the button and speak')
            button.wait_for_press()
                         
            status_ui.status('listening')
            logging.info('Listening...')
            process_event(assistant, status_ui, button)


if __name__ == '__main__':
    main()

