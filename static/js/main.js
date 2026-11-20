/**
 * =============================================================
 * static/js/main.js — JavaScript Principal
 * =============================================================
 * Organização:
 * 1. Dark Mode (toggle e persistência)
 * 2. Navbar (efeito scroll)
 * 3. Inicialização das bibliotecas (AOS, etc.)
 * 4. Utilitários gerais
 * =============================================================
 */

// Executar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function () {
    DarkMode.init();
    Navbar.init();
    Animations.init();
});


/* =============================================================
   1. DARK MODE
   - Guarda preferência no localStorage
   - Respeita preferência do sistema operativo
   ============================================================= */
const DarkMode = {

    // Chave usada para guardar no localStorage
    STORAGE_KEY: 'destinos-banda-theme',

    /**
     * Inicializa o dark mode.
     * Ordem de prioridade:
     * 1. Preferência guardada pelo utilizador
     * 2. Preferência do sistema operativo
     * 3. Light mode por padrão
     */
    init() {
        const savedTheme = localStorage.getItem(this.STORAGE_KEY);
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

        // Aplicar tema guardado ou preferência do sistema
        const initialTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
        this.applyTheme(initialTheme);

        // Ligar o botão de toggle
        const toggleBtn = document.getElementById('darkModeToggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggle());

            // Acessibilidade: suporte a teclado
            toggleBtn.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggle();
                }
            });
        }

        // Ouvir mudanças na preferência do sistema
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            // Só actualizar automaticamente se o utilizador não tiver uma preferência guardada
            if (!localStorage.getItem(this.STORAGE_KEY)) {
                this.applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    },

    /**
     * Aplica um tema ao documento e actualiza a acessibilidade do botão.
     * @param {string} theme - 'dark' ou 'light'
     */
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);

        // Actualizar aria-label para acessibilidade
        const toggleBtn = document.getElementById('darkModeToggle');
        if (toggleBtn) {
            const label = theme === 'dark'
                ? 'Activar modo claro'
                : 'Activar modo escuro';
            toggleBtn.setAttribute('aria-label', label);
        }
    },

    /** Alterna entre dark e light, guardando a preferência. */
    toggle() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        this.applyTheme(newTheme);
        localStorage.setItem(this.STORAGE_KEY, newTheme);
    },

    /** Retorna o tema actual. */
    getCurrent() {
        return document.documentElement.getAttribute('data-theme') || 'light';
    }
};


/* =============================================================
   2. NAVBAR
   - Efeito de scroll: navbar fica mais opaca após descer
   - Fechar menu mobile ao clicar num link
   ============================================================= */
const Navbar = {

    init() {
        const navbar = document.getElementById('mainNavbar');
        if (!navbar) return;

        // Efeito scroll
        this.handleScroll(navbar);
        window.addEventListener('scroll', () => this.handleScroll(navbar), { passive: true });

        // Fechar menu mobile ao clicar num link
        const navLinks = navbar.querySelectorAll('.nav-link-custom');
        const bsCollapse = document.getElementById('navbarMain');

        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                // Fechar o menu Bootstrap se estiver aberto
                if (bsCollapse && bsCollapse.classList.contains('show')) {
                    const bsCollapseInstance = bootstrap.Collapse.getInstance(bsCollapse);
                    if (bsCollapseInstance) bsCollapseInstance.hide();
                }
            });
        });
    },

    /**
     * Adiciona/remove a classe 'scrolled' dependendo da posição de scroll.
     * @param {Element} navbar
     */
    handleScroll(navbar) {
        if (window.scrollY > 20) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    }
};


/* =============================================================
   3. ANIMAÇÕES
   - Inicializar AOS (Animate on Scroll)
   ============================================================= */
const Animations = {

    init() {
        // Verificar se a biblioteca AOS está carregada
        if (typeof AOS !== 'undefined') {
            AOS.init({
                duration: 600,        // Duração das animações em ms
                easing: 'ease-out-cubic',
                once: true,           // Animar apenas uma vez (melhor performance)
                offset: 80,           // Distância do bottom do viewport para iniciar
                disable: 'mobile',    // Desactivar em mobile para melhor performance
            });
        }
    }
};


/* =============================================================
   4. UTILITÁRIOS
   ============================================================= */

/**
 * Formata um número com separadores de milhar em formato angolano.
 * Ex: 1500 → "1 500"
 * @param {number} num
 * @returns {string}
 */
function formatNumber(num) {
    return new Intl.NumberFormat('pt-AO').format(num);
}

/**
 * Trunca um texto a um número máximo de caracteres.
 * @param {string} text
 * @param {number} maxLength
 * @returns {string}
 */
function truncateText(text, maxLength = 100) {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength).trim() + '...';
}

/**
 * Mostra uma mensagem de toast (notificação temporária).
 * Usa os componentes de Toast do Bootstrap.
 * @param {string} message
 * @param {string} type - 'success' | 'error' | 'info' | 'warning'
 */
function showToast(message, type = 'info') {
    // A implementar na Fase 2 com componentes Bootstrap Toast
    console.info(`[Toast ${type}]: ${message}`);
}

// Exportar utilitários para uso global (outros ficheiros JS)
window.DestinosBanda = {
    DarkMode,
    Navbar,
    showToast,
    formatNumber,
    truncateText,
};
