<script lang="ts">
  import { t } from '../i18n'
  import {
    acknowledgeOperatorNotice,
    operatorNotices,
  } from '../stores/announcementStore'
  import { mountOverlay } from '../stores/overlayStack'

  const text = $derived($operatorNotices[0])

  // No closer: only the button dismisses it.
  function open(dialog: HTMLDialogElement) {
    dialog.showModal()
    return mountOverlay('operatorNotice')
  }
</script>

{#if text}
  <dialog
    {@attach open}
    aria-labelledby="operator-notice-title"
    aria-describedby="operator-notice-text"
    oncancel={(event) => event.preventDefault()}
    onkeydown={(event) => event.stopPropagation()}
    onpointerdown={(event) => event.stopPropagation()}
    onclick={(event) => event.stopPropagation()}
    ondblclick={(event) => event.stopPropagation()}
  >
    <h2 id="operator-notice-title">{$t('announcements.title')}</h2>
    <p id="operator-notice-text">{text}</p>
    <div class="actions">
      <button type="button" onclick={acknowledgeOperatorNotice}
        >{$t('common.confirm')}</button
      >
    </div>
  </dialog>
{/if}

<style>
  dialog {
    width: min(420px, calc(100vw - 32px));
    box-sizing: border-box;
    padding: 22px;
    border: 1px solid rgba(240, 192, 64, 0.5);
    border-radius: 10px;
    background: #101820;
    color: #e6edf3;
    font:
      14px/1.6 'Noto Sans KR',
      sans-serif;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    pointer-events: auto;
  }

  dialog::backdrop {
    background: rgba(6, 10, 16, 0.7);
  }

  h2 {
    margin: 0 0 12px;
    font-size: 18px;
    color: #f0c040;
  }

  p {
    margin: 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 18px;
  }

  button {
    padding: 9px 20px;
    border: 1px solid #d2a63c;
    border-radius: 5px;
    background: #604b20;
    color: #fff0c5;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }
</style>
