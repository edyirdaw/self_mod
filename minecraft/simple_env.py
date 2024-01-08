from __future__ import print_function

from builtins import range
import MalmoPython
import os
import sys
import time

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
                          <DrawCuboid x1="-1065" y1="227" z1="25" x2="-1059" y2="237" z2="25" type="gold_block"/>
                    </DrawingDecorator>
                    <!-- <ServerQuitFromTimeUp timeLimitMs="30000"/>  -->
                    <!-- <ServerQuitWhenAnyAgentFinishes/> -->
                </ServerHandlers>
              </ServerSection>

              <AgentSection mode="Creative">
                <Name>SelfMod</Name>
                <AgentStart>
                  <Placement x="-1065.5" y="346.5" z="0.5" pitch="0.0"/>
                  <Inventory/>
                </AgentStart>
                <AgentHandlers>
                  <ObservationFromFullStats/>
                  <ContinuousMovementCommands turnSpeedDegs="180"/>
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

# Loop until mission ends:
while world_state.is_mission_running:
    print(".", end="")
    time.sleep(0.1)
    world_state = agent_host.getWorldState()

    # print('Observations ----------')
    # for i in world_state.observations:
    #     print(i)

    for error in world_state.errors:
        print("Error:",error.text)

print()
print("Mission ended")
# Mission has ended.