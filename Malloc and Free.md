The Unix v6 source code for malloc() and mfree() is surprisingly compact. Both procedures manipulate map structures in order to
keep track of free and allocated memory.

```c
/* Lines 2504 - 2520
 * Structure of the coremap and swapmap
 * arrays. Consists of non-zero count
 * and base address of that many
 * contiguous units.
 * (The coremap unit is 64 bytes, 
 * the swapmap unit is 512 bytes)
 * The addresses are increasing and 
 * the list is terminated with the 
 * first zero count
 */
struct map
{
  char *m_size;
  char *m_addr;
}
```

Let's look at malloc() first.

```c
/* Lines 2522 - 2548
 * Allocate size units from the given
 * map. Return the base of the allocated
 * space.
 * Algorithm is first fit.
 */
malloc(mp, size)
struct map *mp;
{
  register int a;
  register struct map *bp;
  
  for (bp = mp; bp->m_size; bp++) {     /* while there are free blocks on the map... */
    if (bp->m_size >= size) {           /* if the free block has a size > our requested size... */
      a = bp->m_addr;                   /* save the memory address of the free block as 'a' */
      bp->m_addr =+ size;               /* increment the memory address by 'size' units */
      if ((bp->m_size =- size) == 0)    /* remove the block from the free list (and push subsequent blocks down) if size went to 0 */
        do {
            bp++;
            (bp-1)->m_addr = bp->m_addr;
        } while((bp-1)->m_size = bp->m_size);
      return(a);                         /* return the found block */
    }
  }
  return(0);                             /* didn't find a free block of m_size >= size; return 0 */
}
```

Now for mfree()

```c
/* Lines 2550 - 2588
 * Free the previously allocated space aa
 * of size units into the specified map.
 * Sort aa into map and combine on 
 * one or both ends if possible.
 */
mfree(mp, size, aa)
struct map *mp;
{
  register struct map *bp;
  register int t;
  register int a;
  
  a = aa;
  for (bp = mp; bp->m_addr<=a && bp->m_size!=0; bp++);  /* find the first block with nonzero m_size and m_addr > a */
  if (bp>mp && (bp-1)->m_addr+(bp-1)->m_size == a) {    /* if bp isn't the first block and the prior block can be coallesced... */
    (bp-1)->m_size =+ size;                             /* coallesce the prior block with the block we are freeing */
    if (a+size == bp-<m_addr) {                         /* if the newly coallesced block is "up against" the current block... */
      (bp-1)->m_size =+ bp->m_size;                     /* coallesce that block too and adjust the free map accordingly */
      while (bp->m_size) {
        bp++;
        (bp-1)->m_addr = bp->m_addr;
        (bp-1)->m_size = bp->m_size;
      }
    }
  } else {                                              /* can't coallesce the prior block, but... */
    if (a+size == bp->m_addr && bp->m_size) {           /* maybe we can coallesce the current block? */
      bp->m_addr -= size;                               /* yes, we can coallesce! adjust m_addr and m_size and we're done */
      bp->m_size =+ size;
    } else if(size) do {                                /* nope, we can't coallesce anything. add a free block to the list and adjust the free map accordingly */
      t = bp->m_addr;
      bp->m_addr = a;
      a = t;
      t = bp->m_size;
      bp->m_size = size;
      bp++;
    } while (size = t);
  }
}
```
