from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import font_manager
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'figures'; OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','figure.facecolor':'white'})
B='#2563eb'; D='#172554'; G='#e9eef5'

def save(fig,name):
    for ext in ('png','svg'): fig.savefig(OUT/f'{name}.{ext}',dpi=180,bbox_inches='tight',facecolor='white')
    plt.close(fig)
    
def flow(name,title,rows,foot):
    fig,ax=plt.subplots(figsize=(9,1.1*len(rows)+1.4)); ax.set_xlim(0,1); ax.set_ylim(0,len(rows)+.7); ax.axis('off'); ax.set_title(title,fontsize=17,fontweight='bold',pad=12)
    for i,row in enumerate(rows):
        y=len(rows)-i-.25; n=len(row); w=.86/n-.025
        for j,label in enumerate(row):
            x=.07+j*.86/n
            ax.add_patch(FancyBboxPatch((x,y-.43),w,.70,boxstyle='round,pad=0.015',facecolor=G,edgecolor=B,linewidth=1.3)); ax.text(x+w/2,y-.08,label,ha='center',va='center',fontsize=10,color='black')
        if i<len(rows)-1: ax.annotate('',(.5,y-.70),(.5,y-.47),arrowprops={'arrowstyle':'->','color':B,'lw':1.6})
    fig.text(.5,.015,foot,ha='center',fontsize=9,color='#444'); save(fig,name)
flow('01_system_architecture','System integration architecture',[['Frontend / Backend (pending E2E)'],['ROS API Bridge','FleetState from RMF'],['PPO Scheduler: observation + mask + policy'],['Assignment result','Targeted RMF request'],['RMF / Nav2 / Gazebo (pending live verification)']],'Design overview; isolated tests do not establish end-to-end success.')
flow('02_runtime_flow','Runtime dispatch',[['Task request + latest FleetState'],['98-D observation and 7-D action mask'],['Capability / battery / runtime availability'],['Valid actions: PPO prediction','No valid actions: wait or fail'],['Publish assignment / targeted request (if assigned)']],'Runtime filters differ from training environment queue policy.')
fig,ax=plt.subplots(figsize=(8,4)); labels=['Scheduling-only','Runtime','Extended runtime']; counts=[10,12,8]; ax.barh(labels,counts,color=B); ax.invert_yaxis(); ax.set_xlim(0,14); ax.set_xlabel('Unique test cases passed'); ax.set_title('Functional verification: 30 / 30',fontweight='bold');
for i,v in enumerate(counts): ax.text(v+.2,i,f'{v}/{v}',va='center');
ax.spines[['top','right']].set_visible(False); save(fig,'03_test_results')
fig,ax=plt.subplots(figsize=(8,2.7)); import numpy as np
from matplotlib.colors import ListedColormap
arr=np.array([[0,0,1,1,0,0,0],[0,0,0,1,0,0,0]]); ax.imshow(arr,cmap=ListedColormap([G,B]),vmin=0,vmax=1,aspect='auto'); ax.set_xticks(range(7),['C01','C02','M01','M02','W01','W02','W03']); ax.set_yticks([0,1],['Before (FAIL)','After (PASS)']);
for i in range(2):
 for j in range(7): ax.text(j,i,str(arr[i,j]),ha='center',va='center',color='white' if arr[i,j] else 'black',fontweight='bold')
ax.set_title('DEF-01: 31 s stale M01 state'); fig.text(.5,.02,'Selected action: 2 (M01) before / 3 (M02) after',ha='center'); fig.subplots_adjust(bottom=.25); save(fig,'04_stale_mask')
flow('05_unavailable','Observed unavailable-robot behavior',[['No feasible action for specimen task'],['Both busy / charging','Both stale / offline / error'],['Pending: periodic retry','Failed: status 4'],['Fresh eligible robot: predict','No automatic retry established']],'Tested homogeneous conditions; mixed cases and timeout policy not established.')
fig,ax=plt.subplots(figsize=(8,2.8)); ax.barh([1],3.2,left=0,color=G,edgecolor=B); ax.barh([1],.2428873479948379,left=3.2,color=B); ax.axvline(3.2,color=B,linestyle='--'); ax.text(1.6,1,'Pending: 3.2 s',ha='center',va='center'); ax.annotate('Recovery → dispatch\n0.243 s',xy=(3.32,1.2),xytext=(2.5,1.75),arrowprops={'arrowstyle':'->','color':B},ha='center'); ax.set_xlim(0,3.8); ax.set_ylim(.4,2.1); ax.set_yticks([]); ax.set_xlabel('Illustrative elapsed time (s)'); ax.set_title('RT-20: one observed recovery'); ax.spines[['top','right','left']].set_visible(False); save(fig,'06_recovery')
flow('07_concurrent','RT-08: concurrent task assignment',[['Specimen task 1','Specimen task 2','Specimen task 3'],['M01 / Robot 3','M02 / Robot 4','Pending']],'Two assigned, one pending; not a concurrent navigation measurement.')
flow('08_completion','Task completion and return requests',[['Source arrival required'],['Destination arrival → completed'],['RT-11: SOC 100%','RT-12: SOC 20%'],['Parking request','Charging station request']],'Synthetic completion events; physical return and charging remain unverified.')
print('Generated 8 PNG + 8 SVG in',OUT)