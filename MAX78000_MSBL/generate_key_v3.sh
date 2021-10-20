#!/bin/bash
#openssl enc -aes-192-cbc -k secret -P -md sha1

if [ -e key.txt ]
then
    rm key.txt
fi
#rm key.txt | true
key=$(openssl enc -aes-192-cbc -iter 1000 -k secret -P -md sha1 -P | grep -o ..)
#echo $key
printf "aes_key_start\n" >> key.txt
array=(`echo $key | sed 's/,/\n/g'`)
for i in {0..2}
do
for j in {0..7}
do
printf "0x" >> key.txt
printf "${array[$j+i*8+12]}" >> key.txt
printf ", " >> key.txt
done
printf "\n" >> key.txt
done
#echo $key
printf "aes_key_end\n" >> key.txt

key=$(openssl rand -hex 32 | grep -o ..)
printf "aes_aad_start\n" >> key.txt
array=(`echo $key | sed 's/,/\n/g'`)
for i in {0..3}
do
for j in {0..7}
do
printf "0x" >> key.txt
printf "${array[$j+i*8]}" >> key.txt
printf ", " >> key.txt
done
printf "\n" >> key.txt
done
#echo $key
printf "aes_key_end\n" >> key.txt

echo "Key is written to key.txt"
#echo $key | \
#while read CMD; do
#echo 0x$CMD,
#done
