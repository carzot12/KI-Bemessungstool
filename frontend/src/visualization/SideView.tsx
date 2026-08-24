import type { VisualizationModel } from '../types'

const positions = (start: number, end: number, count: number) =>
  count <= 1 ? [(start + end) / 2] : Array.from({ length: count }, (_, i) => start + i * (end - start) / (count - 1))

export default function SideView({ model, dimensions }: { model: VisualizationModel; dimensions: boolean }) {
  const leftX = positions(120, 360, model.rowsParallel)
  const rightX = leftX.map(x => 900 - x).reverse()
  const ys = positions(122, 298, model.rowsPerpendicular)
  const radius = Math.max(6, Math.min(11, model.dowelDiameterMm * .55))
  return <svg className="engineering-svg" viewBox="0 0 900 400" role="img" aria-label="Seitenansicht des Zuglaschenstoßes">
    <defs>
      <linearGradient id="woodSide" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#c99150"/><stop offset="1" stopColor="#8d592e"/></linearGradient>
      <marker id="arrowRed" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M8 0 0 4 8 8" fill="none" stroke="#e2203f" strokeWidth="1.6"/></marker>
    </defs>
    <g className="drawing-fade">
      <rect x="62" y="76" width="388" height="266" rx="2" fill="url(#woodSide)" stroke="#d0a36c"/>
      <rect x="450" y="76" width="388" height="266" rx="2" fill="url(#woodSide)" stroke="#d0a36c"/>
      {Array.from({length: 8}, (_,i)=><path key={i} d={`M70 ${98+i*29} C220 ${88+i*29}, 320 ${108+i*29}, 442 ${96+i*29}`} className="grain"/>)}
      {Array.from({length: 8}, (_,i)=><path key={i} d={`M458 ${98+i*29} C600 ${108+i*29}, 720 ${88+i*29}, 830 ${99+i*29}`} className="grain"/>)}
      <line x1="450" y1="70" x2="450" y2="348" className="joint"/>
      <rect x="300" y="88" width="300" height="242" className="hidden-plate"/>
      <line x1="416" y1="47" x2="366" y2="47" stroke="#e2203f" strokeWidth="3" markerEnd="url(#arrowRed)"/>
      <line x1="484" y1="47" x2="534" y2="47" stroke="#e2203f" strokeWidth="3" markerEnd="url(#arrowRed)"/>
      <text x="450" y="52" textAnchor="middle" className="force">FEd = {model.forceEdKn} kN</text>
      {[...leftX, ...rightX].flatMap((x) => ys.map((y) => <g key={`${x}-${y}`}><circle cx={x} cy={y} r={radius} className="dowel"/><circle cx={x} cy={y} r="2.5" fill="#0b1118"/></g>))}
      <text x="450" y="368" textAnchor="middle" className="svg-label">Stoßfuge</text>
      <g className={`dimensions ${dimensions ? 'visible' : ''}`}>
        <line x1="62" y1="365" x2="838" y2="365" className="dim-line"/>
        <text x="450" y="390" textAnchor="middle">{model.rowsParallel} × {model.rowsPerpendicular} = {model.rowsParallel * model.rowsPerpendicular} je Stoßseite · Ø{model.dowelDiameterMm}</text>
        <line x1="42" y1="76" x2="42" y2="342" className="dim-line"/><text x="25" y="214" transform="rotate(-90 25 214)">h = {model.sectionHeightMm}</text>
      </g>
    </g>
  </svg>
}
