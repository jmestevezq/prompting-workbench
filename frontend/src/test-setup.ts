import '@testing-library/jest-dom/vitest'

// jsdom doesn't implement scrollIntoView — mock it globally
Element.prototype.scrollIntoView = () => {}
