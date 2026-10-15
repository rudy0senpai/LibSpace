import { useEffect, useState } from 'react';

function LampIllustration({ lightOn }) {
  return (
    <svg className="lamp-illustration" viewBox="0 0 360 380" aria-hidden="true">
      <defs>
        <linearGradient id="lampBeamGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffe9a8" stopOpacity=".78" /><stop offset="1" stopColor="#ffe9a8" stopOpacity="0" /></linearGradient>
        <linearGradient id="lampShadeGradient" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="var(--lamp-shade-top)" /><stop offset="1" stopColor="var(--lamp-shade-bottom)" /></linearGradient>
      </defs>
      <path className="lamp-beam" d="M124 131 L40 352 Q180 376 322 352 L210 131 Z" fill="url(#lampBeamGradient)" />
      <ellipse cx="177" cy="349" rx="105" ry="13" className="lamp-shadow" />
      <path d="M168 297 L207 205" className="lamp-arm" />
      <path d="M204 209 L141 144" className="lamp-arm" />
      <circle cx="205" cy="207" r="10" className="lamp-joint" />
      <circle cx="140" cy="143" r="9" className="lamp-joint" />
      <path d="M89 128 Q119 76 205 90 L224 145 Q152 166 82 151 Z" className="lamp-shade" fill="url(#lampShadeGradient)" />
      <path d="M82 151 Q151 173 224 145" className="lamp-shade-rim" />
      <path d="M125 300 Q178 284 230 300 L252 332 Q179 353 102 332 Z" className="lamp-base" />
      <path d="M115 327 Q177 344 241 327" className="lamp-base-highlight" />
      {!lightOn && <g className="lamp-face"><ellipse cx="139" cy="126" rx="5.5" ry="8" /><ellipse cx="174" cy="126" rx="5.5" ry="8" /><path d="M146 139 Q157 151 169 139" /></g>}
      {lightOn && <ellipse cx="157" cy="149" rx="23" ry="5" className="lamp-bulb" />}
    </svg>
  );
}

export default function LampThemeToggle({ lightOn, onToggle }) {
  const [chainPull, setChainPull] = useState(false);
  useEffect(() => {
    if (!chainPull) return undefined;
    const timer = window.setTimeout(() => setChainPull(false), 260);
    return () => window.clearTimeout(timer);
  }, [chainPull]);
  const nextState = lightOn ? 'Turn light off' : 'Turn light on';
  return (
    <div className={`lamp-stage${chainPull ? ' chain-pulled' : ''}`} data-light={lightOn ? 'on' : 'off'}>
      <span className="lamp-orbit lamp-orbit-one" aria-hidden="true" />
      <span className="lamp-orbit lamp-orbit-two" aria-hidden="true" />
      <button type="button" className="lamp-toggle" onClick={() => { setChainPull(true); onToggle(); }} aria-label="Lamp light" aria-describedby="lamp-stage-state" title={nextState} aria-pressed={lightOn}>
        <LampIllustration lightOn={lightOn} />
        <span className="lamp-pull-chain" aria-hidden="true"><i /></span>
        <span className="lamp-stage-label" id="lamp-stage-state">Light {lightOn ? 'ON' : 'OFF'} <small>· pull chain</small></span>
      </button>
      <span className="lamp-stage-caption" aria-live="polite">{lightOn ? 'A little warmth for your next chapter.' : 'A quiet glow in the stacks.'}</span>
    </div>
  );
}
