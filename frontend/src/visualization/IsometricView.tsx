import type { VisualizationModel } from '../types'

export default function IsometricView({model}:{model:VisualizationModel}) {
  const ys=Array.from({length:model.rowsPerpendicular},(_,i)=>160+i*(115/Math.max(model.rowsPerpendicular-1,1)))
  const left=Array.from({length:model.rowsParallel},(_,i)=>190+i*(170/Math.max(model.rowsParallel-1,1)))
  const right=left.map(x=>900-x).reverse()
  return <svg className="engineering-svg" viewBox="0 0 900 400" aria-label="Isometrische Ansicht des Zuglaschenstoßes">
    <polygon points="80,115 450,115 535,65 165,65" className="iso-top"/><polygon points="450,115 820,115 895,65 535,65" className="iso-top"/>
    <rect x="80" y="115" width="370" height="220" className="iso-face"/><rect x="450" y="115" width="370" height="220" className="iso-face"/>
    <line x1="450" y1="110" x2="450" y2="336" className="joint"/>
    {Array.from({length:model.plateCount},(_,i)=><line key={i} x1="300" y1={82+i*14} x2="650" y2={82+i*14} className="slot-plate"/>)}
    {[...left,...right].flatMap(x=>ys.map(y=><circle key={`${x}-${y}`} cx={x} cy={y} r="9" className="dowel"/>))}
    <text x="450" y="374" textAnchor="middle" className="svg-label">Innenliegende Schlitzbleche · vollständiger Zuglaschenstoß</text>
  </svg>
}
