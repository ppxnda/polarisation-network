# External pilot samples (MFRC + CAD)

| File | What |
|---|---|
| `ext_sample_seed11.csv` | 150 Reddit comments in `label_pilot.py` sample format (`post_id, stratum, text, parent_text`): 100 from MFRC and 50 from CAD, drawn at random and shuffled together. Made with `python tools/sample_external.py --mfrc <MFRC parquet> --n-mfrc 100 --n-cad 50 --seed 11`. |
| `claude_labels_v02.csv` | **Practice run.** Claude's labels for all 150 under `codebook_v0.2.md`: `category`, `punitive_score`, `identity_attack`, plus `confidence` and a one-line `rationale`. This is not gold and not an LLM batch run. Claude read the codebook prompt and labelled the posts in a single session, and the other codebook fields were not coded. |

## Read this before hand-labelling

**Don't open `claude_labels_v02.csv` until you have filled your own gold file** (see rule 1 in `../README.md`). To make the template:

```
python label_pilot.py gold-template --sample pilot_samples/ext_sample_seed11.csv --coder jesse
```

The source corpora's own labels (MFRC moral foundations, CAD abuse classes) are not committed. `sample_external.py` writes them to the gitignored `data/ext_sample_key.csv`, and you shouldn't look at them before labelling either.

## Notes on the draw

- **MFRC** has one row per (comment, annotator), with no comment ids and no parent text. The sample is deduplicated on text (17,886 unique comments), and `post_id` is `mfrc_` plus the first 10 hex characters of the text's SHA-1. `parent_text` is empty for every MFRC row, so the relational features are `na`.
- **CAD** is drawn from comments only, in the train, dev and test splits. `post_id` is `cad_` plus the Reddit comment id. 15 of the 50 rows have an empty `parent_text`, because their parent is a post with no body text (5 of them image posts).
- **The draw is unstratified, so expect few punitive posts.** CAD is about 83% Neutral, and most MFRC comments are Non-Moral or Thin Morality. To test the 1 vs 3 boundary, oversample by source label in a later draw.
- **Comments are not all English.** One MFRC comment (r/europe) is in French.

## Licences and attribution

Both sources are released under **Creative Commons Attribution 4.0 International (CC BY 4.0)**, which permits redistribution and adaptation with attribution. The comments are Reddit user content, so the authors' rights and Reddit's terms also apply. Quote paraphrased text in papers.

**MFRC.** Source: <https://huggingface.co/datasets/USC-MOLA-Lab/MFRC> (file `data/train_dedup-00000-of-00001.parquet`, revision `ddc21d2`). Licence: CC BY 4.0, as stated on the dataset card. Cite as: Trager, J. P., Ziabari, A. S., Rahmati, E., Davani, A. M., Golazizian, P., Karimi-Malekabadi, F., Omrani, A., Li, Z., Kennedy, B., Chochlakis, G., Reimer, N. K., Reyes, M., Cheng, K., Wei, M., Merrifield, C., Khosravi, A., Alvarez, E., & Dehghani, M. (2026). The Moral Foundations Reddit Corpus. *Proceedings of LREC 2026*, 6383 to 6407. Changes made: deduplicated on text, annotations removed, 100 rows sampled.

**CAD.** Source: the ConvoKit corpus `contextual-abuse` (<https://convokit.cornell.edu/documentation/cad.html>), originally released on Zenodo (doi:10.5281/zenodo.4881008). Licence: CC BY 4.0, as stated on both the ConvoKit page and the Zenodo record. Cite as: Vidgen, B., Nguyen, D., Margetts, H., Rossini, P., & Tromble, R. (2021). Introducing CAD: the Contextual Abuse Dataset. *Proceedings of NAACL-HLT 2021*. ConvoKit formatting is by Hao Wan; for ConvoKit itself, cite Chang et al. (2020), ConvoKit: A Toolkit for the Analysis of Conversations, *SIGDIAL 2020*. Changes made: annotations removed, parent text attached, 50 comments sampled.

Created 3 Nov 2026.
