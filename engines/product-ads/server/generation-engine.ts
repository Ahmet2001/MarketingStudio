import { randomUUID } from 'node:crypto'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { db, get } from './db'
import { toolById } from './catalog'

interface GenerationRow {
  id: string
  project_id: string
  tool_id: string
  prompt: string
  input_json: string
}

interface ProjectRow {
  tool_id: string
  title: string
  choice: string
  category: string
}

const generatedDirectory = resolve('storage/generated')
const palettes = [
  ['#9b88ff', '#7656e7', '#d881b2'],
  ['#d9e853', '#6cb174', '#efb853'],
  ['#f4b5c7', '#9b4e73', '#5b3465'],
  ['#b7dfea', '#527db6', '#242039'],
]

function escapeXml(value: string): string {
  return value.replace(/[<>&'"]/g, (character) => ({
    '<': '&lt;',
    '>': '&gt;',
    '&': '&amp;',
    "'": '&apos;',
    '"': '&quot;',
  })[character] ?? character)
}

function createPosterSvg(title: string, choice: string, option: number, isVideo: boolean): string {
  const [first, second, accent] = palettes[option % palettes.length]
  const safeTitle = escapeXml(title)
  const safeChoice = escapeXml(choice)
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" role="img" aria-label="${safeTitle} option ${option + 1}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="${first}"/><stop offset=".65" stop-color="${second}"/><stop offset="1" stop-color="${accent}"/></linearGradient>
    <linearGradient id="can" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#171421"/><stop offset=".5" stop-color="#443a52"/><stop offset="1" stop-color="#15121e"/></linearGradient>
    <filter id="shadow"><feDropShadow dx="0" dy="34" stdDeviation="24" flood-opacity=".25"/></filter>
    <pattern id="grid" width="72" height="72" patternUnits="userSpaceOnUse"><path d="M72 0H0V72" fill="none" stroke="#fff" stroke-opacity=".15"/></pattern>
  </defs>
  <rect width="1080" height="1080" fill="url(#bg)"/>
  <rect width="1080" height="1080" fill="url(#grid)"/>
  <circle cx="895" cy="135" r="235" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="3"/>
  <circle cx="950" cy="920" r="165" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="3"/>
  <text x="68" y="82" font-family="Arial,sans-serif" font-size="20" font-weight="700" letter-spacing="5">PRODUCTMARKETER / ${String(option + 1).padStart(2, '0')}</text>
  <g transform="translate(540 495) rotate(${option % 2 === 0 ? 5 : -5})" filter="url(#shadow)">
    <rect x="-128" y="-300" width="256" height="600" rx="46" fill="url(#can)" stroke="#fff" stroke-opacity=".65" stroke-width="10"/>
    <ellipse cx="0" cy="-286" rx="118" ry="24" fill="#d8d3dc"/>
    <text x="0" y="-15" text-anchor="middle" fill="#fff" font-family="Arial,sans-serif" font-size="48" font-weight="800" letter-spacing="8">MONO</text>
    <text x="0" y="32" text-anchor="middle" fill="#ddd6e8" font-family="Arial,sans-serif" font-size="16" letter-spacing="4">OBJECTS</text>
  </g>
  <text x="68" y="938" fill="#181421" font-family="Arial,sans-serif" font-size="55" font-weight="800">${safeTitle.slice(0, 32)}</text>
  <text x="70" y="990" fill="#181421" fill-opacity=".7" font-family="Arial,sans-serif" font-size="26">${safeChoice}</text>
  ${isVideo ? '<g transform="translate(944 80)"><rect x="-68" y="-26" width="136" height="52" rx="16" fill="#171421" fill-opacity=".72"/><text x="0" y="9" text-anchor="middle" fill="#fff" font-family="Arial,sans-serif" font-size="22">00:12</text></g>' : ''}
</svg>`
}

export async function processGeneration(generationId: string): Promise<void> {
  const generation = get<GenerationRow>(`
    SELECT g.id, g.project_id, p.tool_id, g.prompt, g.input_json
    FROM generations g JOIN projects p ON p.id = g.project_id
    WHERE g.id = ?
  `, generationId)
  if (!generation) return
  const project = get<ProjectRow>('SELECT tool_id, title, choice, category FROM projects WHERE id = ?', generation.project_id)
  const tool = project ? toolById.get(project.tool_id) : undefined
  if (!project || !tool) return

  db.prepare('UPDATE generations SET status = ? WHERE id = ?').run('processing', generationId)

  try {
    await mkdir(generatedDirectory, { recursive: true })
    const insertOutput = db.prepare(`
      INSERT INTO outputs (id, generation_id, position, kind, url, thumbnail_url, metadata_json, status, approved, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, 'ready', 0, ?)
    `)
    const outputIds: string[] = []
    for (let index = 0; index < tool.optionCount; index += 1) {
      const outputId = randomUUID()
      const fileName = `${generationId}-${index + 1}.svg`
      const fileUrl = `/media/generated/${fileName}`
      await writeFile(resolve(generatedDirectory, fileName), createPosterSvg(project.title, project.choice, index, tool.outputKind === 'video'), 'utf8')
      insertOutput.run(
        outputId,
        generationId,
        index,
        tool.outputKind,
        fileUrl,
        fileUrl,
        JSON.stringify({ width: 1080, height: 1080, durationSeconds: tool.outputKind === 'video' ? 12 : null }),
        new Date().toISOString(),
      )
      outputIds.push(outputId)
    }

    if (project.tool_id === 'ugc-video') {
      const insertScene = db.prepare(`
        INSERT INTO scenes (id, generation_id, position, title, script, status, output_id, created_at)
        VALUES (?, ?, ?, ?, ?, 'ready', ?, ?)
      `)
      const scenes = [
        ['Hook', 'I finally found a product that keeps up with my mornings.'],
        ['Problem', 'I wanted clean energy without the usual crash.'],
        ['Product moment', 'This is the small-batch Kora citrus cold brew.'],
        ['Call to action', 'Try the seasonal drop while it is still here.'],
      ]
      scenes.forEach(([title, script], index) => {
        insertScene.run(randomUUID(), generationId, index, title, script, outputIds[index], new Date().toISOString())
      })
    }

    db.prepare(`
      UPDATE generations
      SET status = 'complete', usage_json = ?, completed_at = ?
      WHERE id = ?
    `).run(JSON.stringify({ outputCount: tool.optionCount, providerRequests: 1 }), new Date().toISOString(), generationId)
    db.prepare('UPDATE projects SET status = ?, updated_at = ? WHERE id = ?')
      .run('review', new Date().toISOString(), generation.project_id)
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown generation error'
    db.prepare('UPDATE generations SET status = ?, error = ?, completed_at = ? WHERE id = ?')
      .run('error', message, new Date().toISOString(), generationId)
    db.prepare('UPDATE projects SET status = ?, updated_at = ? WHERE id = ?')
      .run('error', new Date().toISOString(), generation.project_id)
  }
}

export function enqueueGeneration(generationId: string): void {
  windowlessTimeout(() => {
    void processGeneration(generationId)
  }, 850)
}

function windowlessTimeout(callback: () => void, delay: number): void {
  setTimeout(callback, delay).unref()
}
