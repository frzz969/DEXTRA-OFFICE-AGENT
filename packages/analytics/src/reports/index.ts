/**
 * Report builder helpers.
 */

import type { MetricPoint } from '../metrics';

export interface ReportSection {
  title: string;
  lines: string[];
}

export interface Report {
  title: string;
  generatedAt: string;
  sections: ReportSection[];
}

export class ReportBuilder {
  readonly #title: string;
  readonly #sections: ReportSection[] = [];

  constructor(title: string) {
    this.#title = title;
  }

  addSection(title: string, lines: string[]): this {
    this.#sections.push({ title, lines });
    return this;
  }

  addMetricSummary(name: string, points: readonly MetricPoint[]): this {
    const total = points.reduce((sum, point) => sum + point.value, 0);
    this.#sections.push({
      title: name,
      lines: [`count=${points.length}`, `total=${total}`],
    });
    return this;
  }

  build(): Report {
    return {
      title: this.#title,
      generatedAt: new Date().toISOString(),
      sections: [...this.#sections],
    };
  }
}
