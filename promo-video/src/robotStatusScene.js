import * as T from "three";
import {GLTFLoader} from "three/addons/loaders/GLTFLoader.js";

const smooth = (f, a, b) => {
  const t = T.MathUtils.clamp((f-a)/(b-a),0,1);
  return t*t*(3-2*t);
};

export async function createRobotStatusScene(canvas, url, distanceScale=1, wholeViewScale=1) {
  const renderer = new T.WebGLRenderer({canvas, alpha:true, antialias:true, preserveDrawingBuffer:true});
  renderer.setSize(830,720,false);
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.13;
  const scene = new T.Scene();
  const camera = new T.PerspectiveCamera(35,830/720,.01,100);
  scene.add(new T.HemisphereLight(0xf7f9ff,0x555c65,1.5));
  for (const [x,y,z,color,intensity] of [[5,8,5,0xffffff,2.4],[2,4,-6,0xe4ecff,1.25],[-4,2,1,0xffeddc,.7]]) {
    const light = new T.DirectionalLight(color,intensity);
    light.position.set(x,y,z);
    scene.add(light);
  }

  let model;
  try {
    model = (await new GLTFLoader().loadAsync(url)).scene;
  } catch (error) {
    renderer.dispose();
    throw error;
  }
  scene.add(model);
  model.updateMatrixWorld(true);
  const whole = new T.Box3().setFromObject(model);
  const head = new T.Box3();
  const arm = new T.Box3();
  model.traverse(mesh => {
    if (!mesh.isMesh) return;
    const zone = mesh.userData.disassembly_zone;
    const link = mesh.userData.source_link || mesh.name;
    if (zone==="head") head.expandByObject(mesh);
    if (zone==="arms" && (/^Link[1-7]_l$/.test(link)||/^left_/i.test(link))) arm.expandByObject(mesh);
  });
  if (head.isEmpty() || arm.isEmpty()) {
    renderer.dispose();
    throw new Error("AGIBOT model zone metadata missing");
  }
  const center = whole.getCenter(new T.Vector3());
  const height = whole.getSize(new T.Vector3()).y;
  const headTarget = head.getCenter(new T.Vector3()).add(new T.Vector3(0,-height*.035,0));
  const armTarget = arm.getCenter(new T.Vector3());
  let previous;
  return {
    draw(frame) {
      const f=frame<132?132:frame>209&&frame<453?209:Math.min(frame,549);
      if (previous===f) return;
      previous=f;
      const orbit=smooth(f,132,209);
      const headFocus=smooth(f,453,477)*(1-smooth(f,484,505));
      const armFocus=smooth(f,484,505)*(1-smooth(f,521,545));
      const wholeReturn=smooth(f,521,549);
      const angle=T.MathUtils.lerp(T.MathUtils.lerp(.30,.71,orbit),.31,wholeReturn)-headFocus*.38+armFocus*.17;
      const distance=height*distanceScale*T.MathUtils.lerp(wholeViewScale,1,Math.max(headFocus,armFocus))*(2.12-.08*orbit-.99*headFocus-1.05*armFocus+.08*wholeReturn);
      const target=center.clone().lerp(headTarget,headFocus).lerp(armTarget,armFocus);
      camera.position.copy(target).add(new T.Vector3(Math.cos(angle)*distance,distance*.107,Math.sin(angle)*distance));
      camera.lookAt(target);
      renderer.render(scene,camera);
    },
    dispose() {
      model.traverse(node => {
        if (node.isMesh) {
          node.geometry.dispose();
          const materials=Array.isArray(node.material)?node.material:[node.material];
          for(const material of materials) material.dispose();
        }
      });
      renderer.dispose();
    },
  };
}
