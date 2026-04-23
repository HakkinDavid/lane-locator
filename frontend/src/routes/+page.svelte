<svelte:options runes={true} />

<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	type ModoFuente = 'archivo' | 'camara';

	let modo = $state<ModoFuente>('archivo');
	let url = $state('');
	let archivo = $state<File | null>(null);
	let vistaPrevia = $state('');
	let resultado = $state('');
	let error = $state('');
	let procesando = $state(false);
	let camaraEncendida = $state(false);
	let iniciandoCamara = $state(false);

	let video = $state<HTMLVideoElement | null>(null);
	let lienzo = $state<HTMLCanvasElement | null>(null);
	let flujo = $state<MediaStream | null>(null);

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

	async function encenderCamara() {
		if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
			error = 'Se te olvida... Que hasta activar la cámara no te defino.';
			return;
		}

		limpiar();
		iniciandoCamara = true;

		try {
			flujo = await navigator.mediaDevices.getUserMedia({
				video: {
					facingMode: { ideal: 'environment' }
				},
				audio: false
			});

			if (video) {
				video.srcObject = flujo;
				await video.play();
			}

			camaraEncendida = true;
		} catch {
			error = 'Tu cámara no se ha prendido. Pero a fuerza no será.';
			apagarCamara();
		} finally {
			iniciandoCamara = false;
		}
	}

	function apagarCamara() {
		flujo?.getTracks().forEach((pista) => pista.stop());
		flujo = null;
		if (video) video.srcObject = null;
		camaraEncendida = false;
	}

	function capturar() {
		if (!video || !lienzo) {
			error = 'Y hoy resulta, que tu cámara no está lista para usarse.';
			return;
		}

		if (!video.videoWidth || !video.videoHeight) {
			error = 'Al capturar, casi casi se te olvida, que no hay imagen entre tú y el app.';
			return;
		}

		lienzo.width = video.videoWidth;
		lienzo.height = video.videoHeight;
		const contexto = lienzo.getContext('2d');
		if (!contexto) {
			error = 'Por mi parte, no puedo procesar la captura.';
			return;
		}

		contexto.drawImage(video, 0, 0, video.videoWidth, video.videoHeight);
		lienzo.toBlob(
			(blob) => {
				if (!blob) {
					error = 'Ni siquiera fue posible generar el archivo.';
					return;
				}

                // el formato blob no es de dios
				ponerArchivo(new File([blob], `captura-${Date.now()}.jpg`, { type: 'image/jpeg' }));
			},
			'image/jpeg',
			0.9
		);
	}

	async function detectar() {
		if (!archivo) {
			error = 'Y hoy resulta, que no confiarías en mí tu galería.';
			return;
		}

		if (!url.trim()) {
			error = 'Al procesar, casi casi se te olvida, que hay que ingresar el URL correcto.';
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
						: `Por mi parte, te devuelvo la respuesta del backend: ${respuesta.status}`
				);
			}

			if (!cuerpo?.overlay) {
				throw new Error('Ni siquiera se dignó a contestarte.');
			}

			resultado = `data:image/png;base64,${cuerpo.overlay}`;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Esa petición ni al backend llegó.';
		} finally {
			procesando = false;
		}
	}

	function cambiarModo(siguiente: ModoFuente) {
		modo = siguiente;
		limpiar();
		if (siguiente === 'archivo') {
			apagarCamara();
            console.log("Carpetazo y aquí no pasó nada.");
		} else {
			console.log('Cámara, carnal. Muestra los benitos o verás al padrecito santo.');
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
		apagarCamara();
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
			<div class="flex gap-2 max-[700px]:flex-wrap">
				<button
					class="cursor-pointer rounded-md border border-gray-400 bg-white px-3 py-2 disabled:cursor-default disabled:opacity-60 {modo ===
					'archivo'
						? 'bg-gray-200'
						: ''}"
					onclick={() => cambiarModo('archivo')}
					type="button"
				>
					Archivo
				</button>
				<button
					class="cursor-pointer rounded-md border border-gray-400 bg-white px-3 py-2 disabled:cursor-default disabled:opacity-60 {modo ===
					'camara'
						? 'bg-gray-200'
						: ''}"
					onclick={() => cambiarModo('camara')}
					type="button"
				>
					Cámara
				</button>
			</div>

			<input
				bind:value={url}
				class="w-80 max-w-full rounded-md border border-gray-400 bg-white px-3 py-2"
				placeholder="URL del servicio de predicción"
				type="url"
			/>
		</div>

		<div class="mb-4 border border-gray-300 bg-white p-4">
			{#if modo === 'archivo'}
				<input
					accept="image/*"
					class="rounded-md border border-gray-400 bg-white px-3 py-2"
					onchange={cambiarArchivo}
					type="file"
				/>
			{:else}
				<div class="grid gap-3">
					<video
						bind:this={video}
						autoplay
						class="block aspect-[4/3] w-full bg-gray-200 object-cover"
						muted
						playsinline
					></video>
					<div class="flex gap-3 max-[700px]:flex-col max-[700px]:items-stretch">
						<button
							class="cursor-pointer rounded-md border border-gray-400 bg-white px-3 py-2 disabled:cursor-default disabled:opacity-60"
							disabled={iniciandoCamara || camaraEncendida}
							onclick={encenderCamara}
							type="button"
						>
							{iniciandoCamara ? 'Iniciando...' : 'Encender'}
						</button>
						<button
							class="cursor-pointer rounded-md border border-gray-400 bg-white px-3 py-2 disabled:cursor-default disabled:opacity-60"
							disabled={!camaraEncendida}
							onclick={capturar}
							type="button"
						>
							Capturar
						</button>
						<button
							class="cursor-pointer rounded-md border border-gray-400 bg-white px-3 py-2 disabled:cursor-default disabled:opacity-60"
							disabled={!camaraEncendida}
							onclick={apagarCamara}
							type="button"
						>
							Apagar
						</button>
					</div>
				</div>
			{/if}

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

		<canvas bind:this={lienzo} class="hidden"></canvas>
	</div>
</div>
