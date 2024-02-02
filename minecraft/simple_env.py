from __future__ import print_function

from builtins import range
import MalmoPython
import numpy as np
import cv2
import os
import sys
import time
import json
from datetime import datetime

if sys.version_info[0] == 2:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
else:
    import functools
    print = functools.partial(print, flush=True)

missionXML = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
            <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

              <About>
                <Summary>Simple Env</Summary>
              </About>

              <ServerSection>
               <ServerInitialConditions>
                 <Time>
                   <StartTime>12000</StartTime>
                   <AllowPassageOfTime>false</AllowPassageOfTime>
                 </Time>
               </ServerInitialConditions>
                <ServerHandlers>
                  <FlatWorldGenerator generatorString="3;7,220*1,5*3,2;3;,biome_1"/>
                    <DrawingDecorator>
                          <DrawCuboid x1="-1072" y1="227" z1="5" x2="-1059" y2="227" z2="5" type="quartz_block"/>
                          <DrawCuboid x1="-1065" y1="227" z1="35" x2="-1059" y2="237" z2="35" type="gold_block"/>
                    </DrawingDecorator>
                    <!-- <ServerQuitFromTimeUp timeLimitMs="30000"/>  -->
                    <!-- <ServerQuitWhenAnyAgentFinishes/> -->
                </ServerHandlers>
              </ServerSection>

              <AgentSection mode="Creative">
                <Name>SelfMod</Name>
                <AgentStart>
                  <Placement x="-1065.5" y="346.5" z="-1.5" pitch="0.0"/>
                  <Inventory/>
                </AgentStart>
                <AgentHandlers>
                  <ObservationFromFullStats/>
                  <ContinuousMovementCommands turnSpeedDegs="180"/>
                  <VideoProducer want_depth="false">
                    <Width>1344</Width>
                    <Height>540</Height>
                  </VideoProducer>
                </AgentHandlers>
              </AgentSection>
            </Mission>'''

# Create default Malmo objects:

agent_host = MalmoPython.AgentHost()
try:
    agent_host.parse( sys.argv )
except RuntimeError as e:
    print('ERROR:',e)
    print(agent_host.getUsage())
    exit(1)
if agent_host.receivedArgument("help"):
    print(agent_host.getUsage())
    exit(0)

save_images = True
if save_images:
    from PIL import Image

class Agent(object):

    def __init__(self, agent_host, action_set):
        self.rep = 0
        self.agent_host = agent_host
        self.action_set = action_set
        self.tolerance = 0.01
        self.date_time = str(datetime.now()).replace(' ','_').replace(':','-')
        self.init_sleep = 15
        self.next_state_sleep = 2
        self.action_count = 0

    def waitForInitialState(self):
        '''Before a command has been sent we wait for an observation of the world and a frame.'''
        # wait for a valid observation
        world_state = self.agent_host.peekWorldState()
        while world_state.is_mission_running and all(e.text == '{}' for e in world_state.observations):
            world_state = self.agent_host.peekWorldState()
        # wait for a frame to arrive after that
        num_frames_seen = world_state.number_of_video_frames_since_last_state
        while world_state.is_mission_running and world_state.number_of_video_frames_since_last_state == num_frames_seen:
            world_state = self.agent_host.peekWorldState()

        time.sleep(self.init_sleep)
        print('\nStarted observing .................')

        world_state = self.agent_host.getWorldState()

        if world_state.is_mission_running:

            assert len(world_state.video_frames) > 0, 'No video frames!?'

            obs = json.loads(world_state.observations[-1].text)
            self.prev_x = obs[u'XPos']
            self.prev_y = obs[u'YPos']
            self.prev_z = obs[u'ZPos']
            self.prev_yaw = obs[u'Yaw']
            print('Initial position:', self.prev_x, ',', self.prev_y, ',', self.prev_z, 'yaw', self.prev_yaw)

            if save_images:
                # save the frame, for debugging
                frame = world_state.video_frames[-1]
                image = Image.frombytes('RGB', (frame.width, frame.height), bytes(frame.pixels))
                self.iFrame = 0
                self.rep = self.rep + 1
                os.mkdir('img/' + self.date_time)
                image.save('img/'+ self.date_time + '/' + '~frame_' + str(self.iFrame).zfill(4) + '_' + self.date_time + '.png')


        return world_state

    def waitForNextState(self):
        '''After each command has been sent we wait for the observation to change as expected and a frame.'''
        # wait for the observation position to have changed
        print('Waiting for observation...', end=' ')
        while True:
            world_state = self.agent_host.peekWorldState()
            if not world_state.is_mission_running:
                print('mission ended.')
                break
            if not all(e.text == '{}' for e in world_state.observations):
                time.sleep(self.next_state_sleep)
                break


        # wait for the render position to have changed
        print('Waiting for render...', end=' ')
        while True:
            world_state = self.agent_host.peekWorldState()
            if not world_state.is_mission_running:
                print('mission ended.')
                break
            if len(world_state.video_frames) > 0:
                time.sleep(self.next_state_sleep)
                break

        num_frames_before_get = len(world_state.video_frames)
        world_state = self.agent_host.getWorldState()

        if save_images:
            # save the frame, for debugging
            if world_state.is_mission_running:
                assert len(world_state.video_frames) > 0, 'No video frames!?'
                frame = world_state.video_frames[-1]
                image = Image.frombytes('RGB', (frame.width, frame.height), bytes(frame.pixels))
                self.iFrame = self.iFrame + 1
                # image.save('img/' + self.date_time + '/' + 'rep_' + str(self.rep).zfill(3) + '_saved_frame_' + str(self.iFrame).zfill(4) + '_' + self.date_time + '.png')
                (im_width, im_height) = image.size
                image_np = np.array(image.getdata()).reshape((im_height, im_width, 3)).astype(np.uint8)
                opencvImage = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
                # (blurred, edges) = self.canny_edge_detection(image_np)
                cv2.imwrite('img/' + self.date_time + '/' + 'frame_' + str(self.iFrame).zfill(4) + '_' + self.date_time + '_1.png',opencvImage)
                # cv2.imwrite('img/' + self.date_time + '/' + 'frame_' + str(self.iFrame).zfill(4) + '_' + self.date_time + '_2_blurred.png',blurred)
                # cv2.imwrite('img/' + self.date_time + '/' + 'frame_' + str(self.iFrame).zfill(4) + '_' + self.date_time + '_3_edges.png',edges)
                # self.find_contours(edges)
                self.detect_objects(image_np)


        if world_state.is_mission_running:
            assert len(world_state.video_frames) > 0, 'No video frames!?'
            num_frames_after_get = len(world_state.video_frames)
            assert num_frames_after_get >= num_frames_before_get, 'Fewer frames after getWorldState!?'
            frame = world_state.video_frames[-1]
            obs = json.loads(world_state.observations[-1].text)
            self.curr_x = obs[u'XPos']
            self.curr_y = obs[u'YPos']
            self.curr_z = obs[u'ZPos']
            self.curr_yaw = obs[u'Yaw']
            print('New position from observation:', self.curr_x, ',', self.curr_y, ',', self.curr_z, 'yaw',
                  self.curr_yaw, end=' ')

            curr_x_from_render = frame.xPos
            curr_y_from_render = frame.yPos
            curr_z_from_render = frame.zPos
            curr_yaw_from_render = frame.yaw
            print('New position from render:', curr_x_from_render, ',', curr_y_from_render, ',', curr_z_from_render,
                  'yaw', curr_yaw_from_render, end=' ')

            self.prev_x = self.curr_x
            self.prev_y = self.curr_y
            self.prev_z = self.curr_z
            self.prev_yaw = self.curr_yaw

        return world_state

    def canny_edge_detection(self,frame):
        # Convert the frame to grayscale for edge detection
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Apply Gaussian blur to reduce noise and smoothen edges
        blurred = cv2.GaussianBlur(src=gray, ksize=(3, 5), sigmaX=0.5)

        # Perform Canny edge detection
        edges = cv2.Canny(blurred, 70, 135)

        return blurred, edges

    # Doesn't work well
    def find_contours(self,edges):

        # Find contours, draw on image and save
        contours, hierarchy = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(edges, contours, -1, (0, 0, 255), 3)

        # Show user what we found
        i = 0
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            print('Contour {}: x={}, y={}, w={}, h={}'.format(i, x, y, w, h))
            i = i + 1

        # Save the result
        cv2.imwrite('img/' + self.date_time + '/' + 'frame_' + str(self.iFrame).zfill(4) + '_' + self.date_time + '_4_contours.png', edges)

    def detect_objects(self, image_np):

        # print(type(edges))
        # print(edges.shape)
        # np.savetxt('img/' + self.date_time + '/' + 'frame_' + str(self.iFrame).zfill(4) + '_' + self.date_time + '_5_values.txt', np.round(edges,2),fmt="%.2f")

        hsv_img = cv2.cvtColor(image_np, cv2.COLOR_BGR2HSV)
        cv2.imwrite('img/' + self.date_time + '/' + 'frame_' + str(self.iFrame).zfill(4) + '_' + self.date_time + '_6_hsv_img.png',hsv_img)

        pass

    def act(self):
        '''Take an action'''
        if self.action_count % 2 == 0:
            self.agent_host.sendCommand('move 0.1')
        else:
            self.agent_host.sendCommand('strafe 0.1')
        # self.agent_host.sendCommand('move 0.1')
        # self.agent_host.sendCommand('move 0')
        # self.agent_host.sendCommand('strafe 1')
        self.action_count += 1
        print('self.action_count =', self.action_count)


my_mission = MalmoPython.MissionSpec(missionXML, True)
my_mission_record = MalmoPython.MissionRecordSpec()

# Attempt to start a mission:
max_retries = 3
for retry in range(max_retries):
    try:
        agent_host.startMission( my_mission, my_mission_record )
        break
    except RuntimeError as e:
        if retry == max_retries - 1:
            print("Error starting mission:",e)
            exit(1)
        else:
            time.sleep(2)

# Loop until mission starts:
print("Waiting for the mission to start ", end=' ')
world_state = agent_host.getWorldState()
while not world_state.has_mission_begun:
    print(".", end="")
    time.sleep(0.1)
    world_state = agent_host.getWorldState()
    for error in world_state.errors:
        print("Error:",error.text)

print()
print("Mission running ", end=' ')

# agent_host.sendCommand("move 1")
# agent_host.sendCommand("jump 1")
# time.sleep(10)
# agent_host.sendCommand("move 0")

agent = Agent(agent_host,'')
world_state = agent.waitForInitialState()

# The main loop. Loop until mission ends:
while world_state.is_mission_running:
    print(".", end="")
    # time.sleep(0.1)

    agent.act()
    world_state = agent.waitForNextState()

    # print('Observations ----------')
    # for i in world_state.observations:
    #     print(i)

    for error in world_state.errors:
        print("Error:",error.text)

print("Mission ended")
# Mission has ended.