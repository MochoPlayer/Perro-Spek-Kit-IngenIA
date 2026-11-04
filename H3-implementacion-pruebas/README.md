# H3 · Implementación y pruebas

**Entregable:** código ejecutable y pruebas en el repositorio.

**Mínimo exigido:** implementación generada con apoyo de IA, revisión del código y **pruebas reproducibles sin necesidad del robot físico**.

**Reparto del trabajo:** [`reparto-modulos.md`](reparto-modulos.md) (interfaz, intérprete, órdenes y robot, y bloque común). **Estado de cada requisito:** [`plan-pruebas.md`](plan-pruebas.md).

## Flujo de trabajo

Cada caja indica en cursiva el documento que produce. Leyenda debajo del diagrama.

```mermaid
flowchart TB
  classDef eq fill:#ffffff,stroke:#334155,color:#0f172a
  classDef ia fill:#ede9fe,stroke:#7c3aed,color:#2e1065
  classDef check fill:#fef3c7,stroke:#d97706,color:#78350f
  classDef hito fill:#0f172a,stroke:#0f172a,color:#ffffff
  classDef par stroke-dasharray:5 4

  subgraph S3["3 · H3 — Implementar y probar"]
    direction LR
    Q["Casos de prueba<br/><i>casos-de-prueba.md</i>"]:::eq
    R["Implementar<br/><i>src/</i>"]:::ia
    S{"¿Pasan las pruebas<br/>sin robot?<br/><i>tests/</i>"}:::check
    T["Revisión de código<br/><i>revision-codigo.md</i>"]:::eq
    M3(["H3"]):::hito
    class Q,R par
    Q & R --> S -- sí --> T --> M3
    S -- no --> R
  end

  subgraph LEY["Leyenda"]
    direction LR
    L1["Tarea del equipo"]:::eq
    L2["La genera la IA,<br/>el equipo revisa"]:::ia
    L3{"Control"}:::check
    L4(["Entrega"]):::hito
    L5["Borde discontinuo:<br/>en paralelo"]:::eq
    L6["Paso<br/><i>documento que produce</i>"]:::eq
    class L5 par
    L1 ~~~ L2 ~~~ L3 ~~~ L4 ~~~ L5 ~~~ L6
  end

  style LEY fill:#ffffff,stroke:#cbd5e1,color:#334155
  style S3 fill:#f8fafc,stroke:#cbd5e1,color:#334155
  S3 ~~~ LEY
```

### Pasos

**A la vez:**
- [ ] Diseñar los casos de prueba → `casos-de-prueba.md`
- [ ] Implementar el primer incremento con IA (`/speckit.implement`) → `src/`

**Después:**
- [ ] Pruebas reproducibles sin el robot → `tests/`. Si fallan, se vuelve a implementar.
- [ ] Revisión del código → `revision-codigo.md`

> La ubicación exacta de `src/` y `tests/` se fija en `plan.md`.

> El detalle de este hito se completará cuando se presente en clase.
