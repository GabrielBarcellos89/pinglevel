// Poses do Link (pacote v3, 30/10/2026). Usar a pose conforme o momento; a de comemoração só depois da validação real.
import descontraido from './link-poses-v3/link-01-descontraido.webp'
import pensativo from './link-poses-v3/link-02-pensativo.webp'
import semEntender from './link-poses-v3/link-03-sem-entender.webp'
import curioso from './link-poses-v3/link-04-curioso.webp'
import comemorando from './link-poses-v3/link-05-comemorando.webp'
import explicando from './link-poses-v3/link-06-explicando.webp'
import incentivando from './link-poses-v3/link-07-incentivando.webp'
import investigando from './link-poses-v3/link-08-investigando.webp'
import surpreso from './link-poses-v3/link-09-surpreso.webp'
import aguardando from './link-poses-v3/link-10-aguardando.webp'

export const POSES = { descontraido, pensativo, semEntender, curioso, comemorando, explicando, incentivando, investigando, surpreso, aguardando }

// Sequência das aulas de seis etapas: abertura, hipótese, explicação, observação, prática e conclusão.
export const POSES_AULA = [descontraido, pensativo, explicando, curioso, incentivando, comemorando]

// Comemorações (30/10/2026): estrela ao concluir aula, polegares ao acertar um desafio, confetes ao concluir
// laboratório e troféu só no desafio final.
import estrela from './link-comemoracao/link-estrela.webp'
import polegares from './link-comemoracao/link-polegares.webp'
import confetes from './link-comemoracao/link-confetes.webp'
import trofeu from './link-comemoracao/link-trofeu.webp'

export const COMEMORACAO = { estrela, polegares, confetes, trofeu }
