<svelte:options runes={true} />

<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	let url = $state('');
	let archivo = $state<File | null>(null);
	let vistaPrevia = $state('');
	let resultado = $state('');
	let error = $state('');
	let procesando = $state(false);

	function limpiar() {
		error = '';
		resultado = '';
	}

	function ponerArchivo(siguiente: File | null) {
		if (vistaPrevia.startsWith('blob:')) URL.revokeObjectURL(vistaPrevia);
		archivo = siguiente;
		limpiar();
		vistaPrevia = siguiente ? URL.createObjectURL(siguiente) : '';
	}

	function cambiarArchivo(evento: Event) {
		const input = evento.currentTarget as HTMLInputElement;
		ponerArchivo(input.files?.[0] ?? null);
	}

	async function detectar() {
		if (!archivo) {
			error = 'Selecciona o captura una imagen.';
			return;
		}

		if (!url.trim()) {
			error = 'Ingresa la URL del backend.';
			return;
		}

		limpiar();
		procesando = true;

		try {
			const datos = new FormData();
			datos.append('file', archivo);
			datos.append('targetUrl', url.trim());

			const respuesta = await fetch('/api/predict', {
				method: 'POST',
				body: datos
			});

			const cuerpo = await respuesta.json();
			if (!respuesta.ok) {
				throw new Error(
					typeof cuerpo?.error === 'string' && cuerpo.error
						? cuerpo.error
						: `Error ${respuesta.status}`
				);
			}

			if (!cuerpo?.overlay) {
				throw new Error('Respuesta inválida del backend.');
			}

			resultado = `data:image/png;base64,${cuerpo.overlay}`;
		} catch (e) {
			error = e instanceof Error ? e.message : 'No fue posible conectar con el backend.';
		} finally {
			procesando = false;
		}
	}

	onMount(() => {
		if (url) return;

		const actual = new URL(window.location.href);
		actual.port = '8000';
		actual.pathname = '/predict';
		actual.search = '';
		actual.hash = '';
		url = actual.toString();
	});

	onDestroy(() => {
		if (vistaPrevia.startsWith('blob:')) URL.revokeObjectURL(vistaPrevia);
	});
</script>

<svelte:head>
	<title>Lane Locator</title>
</svelte:head>

<div class="min-h-screen bg-gray-100 p-6 text-gray-900 max-[700px]:p-4">
	<div class="mx-auto max-w-[1100px]">
		<div
			class="mb-4 flex flex-wrap items-center justify-between gap-3 max-[700px]:flex-col max-[700px]:items-stretch"
		>
			<input
				bind:value={url}
				class="w-80 max-w-full rounded-md border border-gray-400 bg-white px-3 py-2"
				placeholder="URL del servicio de predicción"
				type="url"
			/>
		</div>

		<div class="mb-4 border border-gray-300 bg-white p-4">
			<input
				accept="image/*"
				class="rounded-md border border-gray-400 bg-white px-3 py-2"
				onchange={cambiarArchivo}
				type="file"
			/>

			<div class="flex gap-3 max-[700px]:flex-col max-[700px]:items-stretch">
				<button
					class="cursor-pointer rounded-md border border-gray-400 bg-white px-3 py-2 disabled:cursor-default disabled:opacity-60"
					disabled={!archivo || procesando}
					onclick={detectar}
					type="button"
				>
					{procesando ? 'Procesando...' : 'Detectar carril'}
				</button>
			</div>

			{#if error}
				<p class="mt-3 text-sm text-red-700">{error}</p>
			{/if}
		</div>

		<div class="flex flex-wrap gap-3 max-[700px]:flex-col max-[700px]:items-stretch">
			<div class="flex-[1_1_320px] overflow-hidden border border-gray-300 bg-white">
				{#if vistaPrevia}
					<img
						alt="Imagen seleccionada"
						class="block aspect-[4/3] w-full bg-gray-200 object-cover"
						src={vistaPrevia}
					/>
				{:else}
					<div class="block aspect-[4/3] w-full bg-gray-200 object-cover"></div>
				{/if}
			</div>

			<div class="flex-[1_1_320px] overflow-hidden border border-gray-300 bg-white">
				{#if resultado}
					<img
						alt="Resultado"
						class="block aspect-[4/3] w-full bg-gray-200 object-cover"
						src={resultado}
					/>
				{:else}
					<div class="block aspect-[4/3] w-full bg-gray-200 object-cover"></div>
				{/if}
			</div>
		</div>
	</div>
</div>
