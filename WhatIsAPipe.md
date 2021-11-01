<h1> What is a Pipe? </h1>

A pipe is an essential tool in any Unix programmer's toolkit.
Pipes are used to "daisy-chain" programs together. They allow
the output one program to serve as the input to another?

Pipes were invented by Ken Thompson at the insistence of 
Doug McIlroy. McIlroy had long proposed the idea of a 
mechanism by which programs could be chained together like
a garden hose. <a href="https://thenewstack.io/pipe-how-the-system-call-that-ties-unix-together-came-about"> Read more about the history of pipes here</a>

The history of Unix is extremely interesting, but that's
not the purpose of this note. Instead, this note will take
you through how Pipes were actually implemented by Ken 
Thompson in Unix v6. 

<h1> No really, what is a Pipe? </h1>

A Pipe is a unique kind of Unix file. Pipes are implemented
as FIFO queues, in which the first characters written into 
the Pipe are the first read out. This should make intuitive
sense - if we have the command

```ls | grep *.py```	

grep expects the Pipe's output be ordered exactly as if 
the output of ls had been written to a file, and that file 
had been passed as input to grep. Using a FIFO queue
ensures that characters are read and written in the right
order, and makes managing Pipes significantly easier from a 
conceptual perspective.

To create a pipe, Unix v6 uses the pipe() system call. The pipe()
system call allocates an inode and creates two file structs - one
for reading and one for writing. Various flags are set to tie
everything together. File descriptors are returned in r0 and r1
through the use of the user struct's u.u_ar0 array.

```c
pipe()
{
  register *ip, *rf, *wf;
  int r;

  ip = ialloc(rootdev);       // allocate the inode
  if(ip == NULL)
    return;
  rf = falloc();              // allocate the reading file struct
  if(rf == NULL) {
    iput(ip);
    return;
  }
  r = u.u_ar0[R0];            // save the read end's file descriptor as r
  wf = falloc();              // allocate the writing file struct
  if(wf == NULL) {
    rf->f_count = 0;
    u.u_ofile[r] = NULL;
    iput(ip);
    return;
  }
  u.u_ar0[R1] = u.u_ar0[r0];  // save the write end's file descriptor in r1
  u.u_ar0[R0] = r;
  wf->f_flag = FWRITE|FPIPE;
  wf->f_inode = ip;
  rf->f_flag = FREAD|FPIPE;
  rf->f_inode = ip;
  ip->i_count = 2;
  ip->i_flag = IACC | IUPD;
  ip->i_mode = IALLOC;
}
```

One important note -- if you read the Unix v6 code carefully, you'll see 
the following macro

```#define PIPSIZ 4096```

That's right -- a pipe can have at most 4096 characters. This actually
serves as a key simplifying assumption. In Unix v6, files beyond 4096 
characters are considered large files. From a file system perspective,
this means that, instead of writing the file contents directly to 
allocated blocks of memory, one or more of the blocks of memory actually
serves as an indirect block, holding up to 256 16-bit pointers to other
blocks that contain file contents. This scheme can get even trickier for
huge file. If you're curious, <a href="https://youtube.com/watch?v=vUyKpzg6vYk">Chris Gregg's CS 110 lecture</a> on Unix v6
gives a really good overview of the Unix v6 file system.

The important takeaway here is that large files are tricky. Unix v6
masterfully side steps this trickiness with a single macro definition.

Writing to a pipe is surprisingly straightforward.

```c
writep(fp)
{
  register *rp, *ip, c;
  
  rp = fp;
  ip = rp->f_inode;
  c = u.u_count;
loop:
  /* If all done, return. */
  plock(ip);
  if(c == 0) {
    prele(ip);
    u.u_count = 0;
    return;
  }
  /* If there are not both read and
   * write sides of the pipe active,
   * return error and signal too.
   */
  if(ip->i_count < 2) {
    prele(ip);
    u.u_error = EPIPE;
    psignal(u.u_procp, SIGPIPE);
    return;
  }
  /* If the pipe is full,
   * wait for reads to delete
   * and truncate it
   */
  if(ip->i_sizel == PIPSIZ) {
    ip->i_mode =| IWRITE;
    prele(ip);
    sleep(ip+1, PPIPE);
    goto loop;
  }
  /* Write what is possible and
   * loop back.
   */
  u.u_offset[0] = 0;
  u.u_offset[1] = ip->isizel;
  u.u_count = min(c, PIPSIZ-u.u_offset[1]);
  c =- u.u_count;
  writei(ip);
  prele(ip);
  if(ip->i_mode&IREAD) {
    ip->i_mode =& ~IREAD;
    wakeup(ip + 2);
  }
  goto loop;
}
```

The basic algorithm is this:
  1. Lock the pipe
  2. If there's nothing to write, release the pipe and return
  3. If there's no longer a reader, release the pipe and signal an error
  4. If the pipe is full, release the Pipe, waiting for it to empty a little
  5. Write as much as possible
     i. Note that, in the best possible situation, we can write 4096 characters.
        Lots of commands produce more than 4096 characters to write. As a result,
        the "goto loop" statement after the write is likely to be hit often.
  6. Release the pipe, and potentially sleep if there's a reader ready
  7. Goto step 1

That's all there is to it! Reading from a pipe is similarly simple.

```c
readp()
int *fp;
{
  register *rp, *ip;
  
  fp = fp;
  ip = rp->f_inode;
loop:
  plock(ip);
  /* If the head (read) has caught up to the tail (write),
   * reset both to 0.
   */
  if(rp->f_offset[1] == ip->i_sizel) {
    if(rp->f_offset[1] != 0) {
      rp->f_offset[1] = 0;
      ip->i_sizel = 0;
      if(ip->i_mode & IWRITE) {
        ip->i_mode =& ~IWRITE;
        wakeup(ip + 1);
      }
    }
    /* If there are not both reader and writer active, 
     * return without satisfying the read 
     */
    prele(ip);
    if(ip->i_count < 2)
      return;
    ip->i_mode =| IREAD;
    sleep(ip + 2, PPIPE);
    goto loop;
  }
  /* Read and return
   */
  u.u_offset[0] = 0;
  u.u_offset[1] = rp->f_offset[1];
  readi(ip);
  rp->f_offset[1] = u.u_offset[1];
  prele(ip);
}
```

The basic algorithm is this:
  1. Lock the pipe
  2. If the reader has caught up with the writer, reset both to 0
     i. If the writer is sleeping, wake it up
     ii. If there's no longer a writer, release the pipe and return without satisfying the read
     iii. Goto step 1
  3. Read from the pipe and retun

The plock(ip) and prele(ip) calls are just for locking and unlocking the underlying
pipe inodes. They also wake up appropriate processes when needed. Both have straightforward
implementations:

```c
plock(ip)
int *ip;
{
  register *rp;

  rp = ip;
  while(rp->i_flag & ILOCK) {
    rp->i_flag =| IWANT;
    sleep(rp, PPIPE);
  }
  rp->i_flag =| ILOCK;
}

prele(ip)
int *ip;
{
  register *rp;
  
  rp = ip;
  rp->i_flag =& ~ILOCK;
  if(rp->i_flag & IWANT) {
    rp->i_flag =& ~IWANT;
    wakeup(rp);
  }
}
```

<h1> Is that it? </h1>
Yup. However, if you're interested, you might want to read about FIFOs, or named pipes. 
Named pipes are exactly what they sound like - pipes that are named. But while pipes
only last for the duration of the processes reading and writing from them, a named pipe
can last for as long as the system is online. As a result, named pipes can be used for
much more widespread IPC. The <a href=https://en.wikipedia.org/wiki/Named_pipe> Wikipedia
page </a> is a good jumping off point.

