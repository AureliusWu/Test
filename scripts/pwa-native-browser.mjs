// Read native state and perform real browser input; no injected game actions.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

const story=JSON.parse(await fs.readFile(new URL('../game/data/story.json',import.meta.url),'utf8'));
const firstLine=story.nodes.find(node=>node.id==='p00_entry').lines[0].text;
export const visibleNarration='renpy.get_screen("say") and renpy.get_screen("say").scope.get("what")';

export const get = async (page, expression) => Promise.race([
    // The official command bridge uses btoa; Python string escapes keep
    // authored Chinese text exact while sending ASCII source commands.
    page.evaluate(expression => window.renpy_get(expression), expression.replace(/[^\x00-\x7f]/g,character=>'\\u'+character.charCodeAt(0).toString(16).padStart(4,'0'))),
    new Promise((_,reject) => setTimeout(() => reject(new Error(`Ren'Py read timed out: ${expression}`)), 5000))]);
export async function waitNative(page, expression) {
    const deadline=Date.now()+60000;
    while (Date.now()<deadline) {
        if (await get(page,expression)) return;
        await page.waitForTimeout(100);
    }
    throw new Error(`Native condition timed out: ${expression}`);
}
export async function clickVirtual(page, x, y) {
    const box = await page.locator('#canvas').boundingBox();
    const scale = Math.min(box.width/1920, box.height/1080);
    await page.mouse.click(box.x+(box.width-1920*scale)/2+x*scale, box.y+(box.height-1080*scale)/2+y*scale);
}
export async function clickId(page, screen, id) {
    await waitNative(page,`bool(renpy.get_displayable(${JSON.stringify(screen)},${JSON.stringify(id)}))`);
    await waitNative(page,'not any(renpy.get_ongoing_transition(layer) for layer in (None, "master", "screens"))');
    // Read the same render-tree geometry used by official Ren'Py testfocus.
    // This command only observes displayables; the following real mouse click
    // performs the action (no injected Start, Save, Load or state mutation).
    const position=await page.evaluate(async({screen,id})=>window.renpy_exec(`
d = renpy.get_displayable(${JSON.stringify(screen)}, ${JSON.stringify(id)})
stack = [(renpy.display.render.screen_render, 0, 0)]
result = None
while stack:
    r, x, y = stack.pop()
    if not isinstance(r, renpy.display.render.Render):
        continue
    if d in r.render_of:
        result = [x + r.width / 2, y + r.height / 2]
        break
    for c in r.children:
        stack.append((c[0], x + c[1], y + c[2]))
`),{screen,id});
    assert.ok(position,`Rendered focus target ${screen}:${id}`);
    await clickVirtual(page,...position);
}
export async function startNarrative(page) {
    await clickId(page,'main_menu','menu_start');
    for(let attempt=0;attempt<10;attempt++) {
        await page.waitForTimeout(200);
        if (await get(page,`${visibleNarration} == ${JSON.stringify(firstLine)}`)) {
            await waitNative(page,'not any(renpy.get_ongoing_transition(layer) for layer in (None, "master", "screens"))');
            return;
        }
        await page.keyboard.press('Space');
    }
    throw new Error('Actual Start did not reach native narration');
}
