export function createRobotStatusScene(canvas:HTMLCanvasElement,url:string,distanceScale?:number,wholeViewScale?:number,showcase?:boolean,workspace?:boolean):Promise<{
  draw(frame:number):void;
  drawOrbit(angle:number):void;
  dispose():void;
}>;
