import type { VisualizationModel } from '../types'

export default function SectionView({ model, dimensions }: { model: VisualizationModel; dimensions: boolean }) {
  const x0=70, full=760, scale=full/model.sectionWidthMm
  const layers = model.plateCount === 2
    ? [model.sideThicknessMm, model.plateThicknessMm, model.middleThicknessMm, model.plateThicknessMm, model.sideThicknessMm]
    : [model.sideThicknessMm, model.plateThicknessMm, model.sideThicknessMm]
  let cursor=x0
  const boxes=layers.map((value,index)=>{const x=cursor; const w=value*scale; cursor+=w; return {x,w,value,index}})
  const ys=Array.from({length:model.rowsPerpendicular},(_,i)=>132+i*(156/Math.max(model.rowsPerpendicular-1,1)))
  return <svg className="engineering-svg" viewBox="0 0 900 400" role="img" aria-label="Querschnitt durch Holz und innenliegende Stahlbleche">
    <defs><linearGradient id="woodSection" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#c99555"/><stop offset="1" stopColor="#8b572d"/></linearGradient></defs>
    <rect x={x0} y="94" width={full} height="230" fill="url(#woodSection)" stroke="#d0a36c"/>
    {boxes.filter(b=>b.index%2===1).map(b=><rect key={b.index} x={b.x} y="94" width={Math.max(3,b.w)} height="230" className="steel"/>)}
    {ys.map(y=><line key={y} x1={x0} y1={y} x2={x0+full} y2={y} className="dowel-axis"/>)}
    <g className={`dimensions ${dimensions?'visible':''}`}>
      <line x1={x0} y1="66" x2={x0+full} y2="66" className="dim-line"/><text x="450" y="54" textAnchor="middle">b = {model.sectionWidthMm} mm</text>
      {boxes.map((b,i)=><g key={i}><line x1={b.x} y1="342" x2={b.x+b.w} y2="342" className="dim-line"/><text x={b.x+b.w/2} y="364" textAnchor="middle">{b.value}</text></g>)}
      <text x="450" y="390" textAnchor="middle">{model.plateCount===2?'t1 · ts · t2 · ts · t1':'t1 · ts · t1'}</text>
    </g>
  </svg>
}
