import { initAccordionMenu } from './app_shell.js';
import { bootstrapInventory, bindInventoryEvents } from './inventory_controller.js';
import { bindEmbeddedPanelTriggers } from './partials_controller.js';

async function bootstrap() {
    initAccordionMenu();
    bindInventoryEvents();
    await bootstrapInventory();
    bindEmbeddedPanelTriggers();
}

bootstrap();
