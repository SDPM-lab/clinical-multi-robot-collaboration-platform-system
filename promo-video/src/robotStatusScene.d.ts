export function createRobotStatusScene(canvas:HTMLCanvasElement,url:string,distanceScale?:number,wholeViewScale?:number):Promise<{
  draw(frame:number):void;
  dispose():void;
}>;
