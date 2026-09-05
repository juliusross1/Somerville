#!/bin/sh
glyphs_start=$(date +%s)
glyphs export --app 4.1 --plugins '' --config somerville_glyphs.config
glyphs_status=$?
glyphs_end=$(date +%s)
glyphs_elapsed=$((glyphs_end - glyphs_start))
echo "glyphs export finished with exit ${glyphs_status} in ${glyphs_elapsed}s"

if [ "$glyphs_status" -ne 0 ]; then
  exit "$glyphs_status"
fi

cp ~/Documents/Somerville/fonts/Somerville/SomervilleMATH-Regular.ttf .
ttx -t MATH SomervilleMATH-Regular.ttf 
ttx -m SomervilleVF.ttf SomervilleMATH-Regular.ttx  -o SomervilleVF-withMathtable.ttf
rm ./SomervilleMATH-Regular.ttx
./fix_avar2_overlapping_regions.sh SomervilleVF-withMathtable.ttf SomervilleVF-withMathtable.ttf

