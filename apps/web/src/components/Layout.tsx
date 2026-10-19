import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { ArrowUpRight, Github, MapPin } from 'lucide-react'

export function Layout({ children }: { children: ReactNode }) {
  return <><a className="skip-link" href="#main">Skip to content</a><div className="site-shell">
    <header className="site-header"><div className="page-wrap header-inner">
      <Link to="/" className="brand" aria-label="L’Escalographe, home"><span className="brand-mark" aria-hidden="true"><span>▰</span><span>▰</span><span>▰</span></span><span><strong>L’Escalographe</strong><small>MONTRÉAL ESCALATOR ATLAS</small></span></Link>
      <nav aria-label="Main navigation"><NavLink to="/" end>Atlas</NavLink><NavLink to="/about">How it works</NavLink><a href="/docs" target="_blank" rel="noreferrer">API <ArrowUpRight size={13} aria-hidden="true" /></a></nav>
    </div></header>
    <main id="main">{children}</main>
    <footer className="site-footer"><div className="page-wrap footer-inner"><div><div className="footer-brand"><MapPin size={15} /> Made for Montréal. Independent of the STM.</div><p>Statuses come from source observations, not predictions. Map data © OpenStreetMap contributors.</p></div><div className="footer-links"><Link to="/about">Methodology</Link><a href="/docs">Open API</a><a href="https://github.com/search?q=montreal-escalators&type=repositories" target="_blank" rel="noreferrer" aria-label="Find project on GitHub"><Github size={16} /></a></div></div></footer>
  </div></>
}
