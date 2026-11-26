import { RobotStatusPhaseV13 } from "./RobotStatusPhaseV13";
import { RobotStatusPhaseV12 } from "./RobotStatusPhaseV12";
import { RobotStatusPhaseV11 } from "./RobotStatusPhaseV11";
import { RobotStatusPhaseV10 } from "./RobotStatusPhaseV10";
import { RobotStatusPhaseV9 } from "./RobotStatusPhaseV9";
import { RobotStatusPhaseV8 } from "./RobotStatusPhaseV8";
import { RobotStatusPhaseV7 } from "./RobotStatusPhaseV7";
import { RobotStatusPhaseV6 } from "./RobotStatusPhaseV6";
import { RobotStatusPhaseV5 } from "./RobotStatusPhaseV5";
import { RobotStatusPhaseV4 } from "./RobotStatusPhaseV4";
import { RobotStatusPhaseV3 } from "./RobotStatusPhaseV3";
import { RobotStatusPhaseV2 } from "./RobotStatusPhaseV2";
import { RobotStatusPhaseV1 } from "./RobotStatusPhaseV1";
import { LiveMapPhaseV3_3 } from "./LiveMapPhaseV3_3";
import { TaskCreationPhaseVNext } from "./TaskCreationPhaseVNext";
import { LiveMapPhaseV3_2 } from "./LiveMapPhaseV3_2";
import { LiveMapPhaseV3_1 } from "./LiveMapPhaseV3_1";
import { LiveMapPhaseV3 } from "./LiveMapPhaseV3";
import { LiveMapPhaseV2 } from "./LiveMapPhaseV2";
import { LiveMapTrackingPrototypeV2 } from "./LiveMapTrackingPrototypeV2";
import { LiveMapTrackingPrototype } from "./LiveMapTrackingPrototype";
import { PPOSchedulingPrototypeV9 } from "./PPOSchedulingPrototypeV9";
import { PPOSchedulingPrototypeV8 } from "./PPOSchedulingPrototypeV8";
import { PPOSchedulingPrototypeV7 } from "./PPOSchedulingPrototypeV7";
import { PPOSchedulingPrototypeV6 } from "./PPOSchedulingPrototypeV6";
import { PPOSchedulingPrototypeV5 } from "./PPOSchedulingPrototypeV5";
import { PPOSchedulingPrototypeV4 } from "./PPOSchedulingPrototypeV4";
import { PPOSchedulingPrototypeV2 } from "./PPOSchedulingPrototypeV2";
import { PPOSchedulingV2Keyframes } from "./PPOSchedulingV2Keyframes";
import { PPOSchedulingPrototype } from "./PPOSchedulingPrototype";
import { TaskCreationPrototypeV10 } from "./TaskCreationPrototypeV10";
import { TaskCreationPrototypeV9 } from "./TaskCreationPrototypeV9";
import { TaskCreationPrototypeV8Fast } from "./TaskCreationPrototypeV8Fast";
import { TaskCreationPrototypeV7 } from "./TaskCreationPrototypeV7";
import { TaskCreationV7Keyframes } from "./TaskCreationV7Keyframes";
import { TaskCreationPrototypeV6 } from "./TaskCreationPrototypeV6";
import { TaskCreationPrototypeV5 } from "./TaskCreationPrototypeV5";
import { TaskCreationPrototypeV4 } from "./TaskCreationPrototypeV4";
import { TaskCreationPrototypeV3 } from "./TaskCreationPrototypeV3";
import { TaskCreationPrototype } from "./TaskCreationPrototype";
import { TaskCreationPrototypeV2 } from "./TaskCreationPrototypeV2";
import { DashboardRevealV5 } from "./DashboardRevealV5";
import { DashboardRevealV4 } from "./DashboardRevealV4";
import { DashboardRevealV3 } from "./DashboardRevealV3";
import { MyComposition } from "./Composition";
import { Composition } from "remotion";
import { DashboardRevealV2 } from "./DashboardRevealV2";
import { DashboardReveal } from "./DashboardReveal";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <MyComposition />
      <Composition id="RobotStatusPhaseV13" component={RobotStatusPhaseV13} width={1920} height={1080} fps={30} durationInFrames={345} />
      <Composition id="RobotStatusPhaseV12" component={RobotStatusPhaseV12} width={1920} height={1080} fps={30} durationInFrames={330} />
      <Composition id="RobotStatusPhaseV11" component={RobotStatusPhaseV11} width={1920} height={1080} fps={30} durationInFrames={240} />
      <Composition id="RobotStatusPhaseV10" component={RobotStatusPhaseV10} width={1920} height={1080} fps={30} durationInFrames={195} />
      <Composition id="RobotStatusPhaseV9" component={RobotStatusPhaseV9} width={1920} height={1080} fps={30} durationInFrames={195} />
      <Composition id="RobotStatusPhaseV8" component={RobotStatusPhaseV8} width={1920} height={1080} fps={30} durationInFrames={300} />
      <Composition id="RobotStatusPhaseV7" component={RobotStatusPhaseV7} width={1920} height={1080} fps={30} durationInFrames={240} />
      <Composition id="RobotStatusPhaseV6" component={RobotStatusPhaseV6} width={1920} height={1080} fps={30} durationInFrames={180} />
      <Composition id="RobotStatusPhaseV5" component={RobotStatusPhaseV5} width={1920} height={1080} fps={30} durationInFrames={360} />
      <Composition id="RobotStatusPhaseV4" component={RobotStatusPhaseV4} width={1920} height={1080} fps={30} durationInFrames={360} />
      <Composition id="RobotStatusPhaseV3" component={RobotStatusPhaseV3} width={1920} height={1080} fps={30} durationInFrames={360} />
      <Composition id="RobotStatusPhaseV2" component={RobotStatusPhaseV2} width={1920} height={1080} fps={30} durationInFrames={600} />
      <Composition id="RobotStatusPhaseV1" component={RobotStatusPhaseV1} width={1920} height={1080} fps={30} durationInFrames={600} />
      <Composition id="Phase3" component={LiveMapPhaseV3_3}
        width={1920} height={1080} fps={30} durationInFrames={600} />
      <Composition id="LiveMapPhaseV3-2" component={LiveMapPhaseV3_2}
        width={1920} height={1080} fps={30} durationInFrames={600} />
      <Composition id="LiveMapPhaseV3-1" component={LiveMapPhaseV3_1}
        width={1920} height={1080} fps={30} durationInFrames={540} />
      <Composition id="LiveMapPhaseV3" component={LiveMapPhaseV3}
        width={1920} height={1080} fps={30} durationInFrames={540} />
      <Composition id="LiveMapPhaseV2" component={LiveMapPhaseV2}
        width={1920} height={1080} fps={30} durationInFrames={450} />
      <Composition id="LiveMapTrackingPrototypeV2" component={LiveMapTrackingPrototypeV2}
        width={1920} height={1080} fps={30} durationInFrames={450} />
      <Composition id="LiveMapTrackingPrototype" component={LiveMapTrackingPrototype}
        width={1920} height={1080} fps={30} durationInFrames={420} />
      <Composition id="PPOSchedulingPrototypeV9" component={PPOSchedulingPrototypeV9}
        width={1920} height={1080} fps={30} durationInFrames={720} />
      <Composition id="PPOSchedulingPrototypeV8" component={PPOSchedulingPrototypeV8}
        width={1920} height={1080} fps={30} durationInFrames={600} />
      <Composition id="PPOSchedulingPrototypeV7" component={PPOSchedulingPrototypeV7}
        width={1920} height={1080} fps={30} durationInFrames={600} />
      <Composition id="PPOSchedulingPrototypeV6" component={PPOSchedulingPrototypeV6}
        width={1920} height={1080} fps={30} durationInFrames={600} />
      <Composition id="PPOSchedulingPrototypeV5" component={PPOSchedulingPrototypeV5}
        width={1920} height={1080} fps={30} durationInFrames={540} />
      <Composition id="PPOSchedulingPrototypeV4" component={PPOSchedulingPrototypeV4}
        width={1920} height={1080} fps={30} durationInFrames={450} />
      <Composition id="PPOSchedulingPrototypeV2" component={PPOSchedulingPrototypeV2}
        width={1920} height={1080} fps={30} durationInFrames={450} />
      <Composition id="PPOSchedulingV2Keyframes" component={PPOSchedulingV2Keyframes}
        width={1920} height={1080} fps={30} durationInFrames={6} />
      <Composition id="PPOSchedulingPrototype" component={PPOSchedulingPrototype}
        width={1920} height={1080} fps={30} durationInFrames={360} />
      <Composition id="Phase2" component={TaskCreationPhaseVNext}
        width={1920} height={1080} fps={30} durationInFrames={495} />
      <Composition id="TaskCreationPrototypeV10" component={TaskCreationPrototypeV10}
        width={1920} height={1080} fps={30} durationInFrames={495} />
      <Composition id="TaskCreationPrototypeV9" component={TaskCreationPrototypeV9}
        width={1920} height={1080} fps={30} durationInFrames={420} />
      <Composition id="TaskCreationPrototypeV8Fast" component={TaskCreationPrototypeV8Fast}
        width={1920} height={1080} fps={30} durationInFrames={420} defaultProps={{reference:false}} />
      <Composition id="TaskCreationPrototypeV8" component={TaskCreationPrototypeV8Fast}
        width={1920} height={1080} fps={30} durationInFrames={585} defaultProps={{reference:true}} />
      <Composition
        id="TaskCreationPrototypeV7"
        component={TaskCreationPrototypeV7}
        width={1920} height={1080} fps={30} durationInFrames={585}
        defaultProps={{ voiceover: "task-creation-v4/voice.wav" }}
      />
      <Composition
        id="TaskCreationV7Keyframes"
        component={TaskCreationV7Keyframes}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={3}
      />
      <Composition
        id="TaskCreationPrototypeV6"
        component={TaskCreationPrototypeV6}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={585}
        defaultProps={{ voiceover: "task-creation-v4/voice.wav" }}
      />
      <Composition
        id="TaskCreationPrototypeV5"
        component={TaskCreationPrototypeV5}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={540}
        defaultProps={{ voiceover: "task-creation-v4/voice.wav" }}
      />
      <Composition
        id="TaskCreationPrototypeV4"
        component={TaskCreationPrototypeV4}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={510}
        defaultProps={{ voiceover: "task-creation-v4/voice.wav" }}
      />
      <Composition
        id="TaskCreationPrototypeV3"
        component={TaskCreationPrototypeV3}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={480}
        defaultProps={{ voiceover: "task-creation/v3-voice.wav" }}
      />
      <Composition
        id="TaskCreationPrototypeV2"
        component={TaskCreationPrototypeV2}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={585}
      />
      <Composition
        id="TaskCreationPrototype"
        component={TaskCreationPrototype}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={540}
        defaultProps={{ voiceover: "voice.mp3" }}
      />
      <Composition
        id="Phase1"
        component={DashboardRevealV5}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={300}
        defaultProps={{ voiceover: "" }}
      />
      <Composition
        id="DashboardRevealV4"
        component={DashboardRevealV4}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={300}
        defaultProps={{ voiceover: "dashboard-v4/voice.mp3" }}
      />
      <Composition
        id="DashboardRevealV3"
        component={DashboardRevealV3}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={300}
        defaultProps={{ voiceover: "dashboard-v3/voice.mp3" }}
      />
      <Composition
        id="DashboardRevealV2"
        component={DashboardRevealV2}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={300}
      />
      <Composition
        id="DashboardRevealPrototype"
        component={DashboardReveal}
        width={1920}
        height={1080}
        fps={30}
        durationInFrames={300}
      />
    </>
  );
};
