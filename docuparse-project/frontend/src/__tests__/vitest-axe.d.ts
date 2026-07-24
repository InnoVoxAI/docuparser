import type { AxeMatchers } from 'vitest-axe'

// vitest-axe@0.1.0 declara seus tipos via `namespace Vi` (mecanismo de
// matcher customizado de Vitest 2+); este projeto está em Vitest 1.4, que usa
// `declare module 'vitest'` (ver "Extending Matchers" nos docs do Vitest 1.x).
// Sem esta augmentation local, `toHaveNoViolations` não é reconhecido por `tsc`
// mesmo com o matcher registrado em runtime via `expect.extend` (setup.ts).
declare module 'vitest' {
    // eslint-disable-next-line @typescript-eslint/no-empty-object-type -- padrão oficial de augmentation do Vitest 1.x para matchers customizados.
    interface Assertion extends AxeMatchers {}
    // eslint-disable-next-line @typescript-eslint/no-empty-object-type -- padrão oficial de augmentation do Vitest 1.x para matchers customizados.
    interface AsymmetricMatchersContaining extends AxeMatchers {}
}
