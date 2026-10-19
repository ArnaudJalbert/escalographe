import { useLanguage } from '../i18n'
import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { ArrowUpRight, Github, MapPin } from 'lucide-react'

export function Layout({ children }: { children: ReactNode }) {
  const { t, locale, setLocale } = useLanguage()
  return <><a className="skip-link" href="#main">{t('Skip to content')}</a><div className="site-shell">
    <header className="site-header"><div className="page-wrap header-inner">
      <Link to="/" className="brand" aria-label={t('L’Escalographe, home')}><span className="brand-mark" aria-hidden="true"><span>▰</span><span>▰</span><span>▰</span></span><span><strong>L’Escalographe</strong><small>{t('MONTRÉAL ESCALATOR ATLAS')}</small></span></Link>
      <nav aria-label={t('Main navigation')}><NavLink to="/" end>Atlas</NavLink><NavLink to="/about">{t('How it works')}</NavLink><a href="/docs" target="_blank" rel="noreferrer">API <ArrowUpRight size={13} aria-hidden="true" /></a></nav><div className="language-switch" role="group" aria-label={locale === "fr" ? "Langue" : "Language"}><button type="button" lang="fr" aria-pressed={locale === "fr"} onClick={() => setLocale("fr")}>Français</button><button type="button" lang="en" aria-pressed={locale === "en"} onClick={() => setLocale("en")}>English</button></div>
    </div></header>
    <main id="main">{children}</main>
    <footer className="site-footer"><div className="page-wrap footer-inner"><div><div className="footer-brand"><MapPin size={15} /> {t('Made for Montréal. Independent of the STM.')}</div><p>{t('Statuses come from source observations, not predictions. Map data © OpenStreetMap contributors.')}</p></div><div className="footer-links"><Link to="/about">{t('Methodology')}</Link><a href="/docs">{t("Open API")}</a><a href="https://github.com/ArnaudJalbert/escalographe" target="_blank" rel="noreferrer" aria-label={t("Find project on GitHub")}><Github size={16} /></a></div></div></footer>
  </div></>
}
