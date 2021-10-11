<h1>How does Unixv6 start?</h1>

Unix v6 starts at line 0612 in the source. At this point in time, the machine (presumably a PDP 11/40 or something similar) has nothing initialized. The goal of the Unixv6 start
sequence is to initialize a couple of things:

<h1> Segmentation Registers </h1>

The segmentation registers for user space and kernel space. These segmentation registers actually refer 
to a pair of registers: the page address register (the PAR) and the page descriptor register (the PDR). 
The page address register is used to decode virtual addresses into physical ones (with the caveat that 
this translation only occurs if the memory management unit is on). The layout of the PAR is as follows:
        
<img src=images/PAR.png alt=PAR Bitwise Layout>

The virtual addressing algorithm combines the information in the PAR with the given virtual address
to determine a physical address

<img src=images/va_to_pa_algo.PNG alt=VA Algorithm>

The PDR, on the other hand, specifies the length of the memory area (called a page - more on that later). 
The PDR also specifies permissions that control memory access. The layout of the PDR is below:

<img src=images/PDR.PNG alt=PDR Bitwise Layout>

As mentioned above, the machine actually keeps two sets of segmentation registers - one for when the
machine is in user mode, and another for one the machine is in kernel mode. The mode of the machine
is determined by a register called the Processor Status Word (PS) - but more on that later.

<img src=images/segmentation_regs.PNG alt=Segmentation Registers>

Setting the segmentation registers up appropriately will help ensure a clean split between user space
and kernel space. This setup is also relevant once we start delving into process memory.

<h1> Process #0 </h1>

Process #0 (colloquially named "The First Process") is the first process that the computer sees on 
startup. Being the first process, Process #0 requires special setup. Unix v6 starts performing this
setup on line 0646, although it takes a while for this setup to complete. 

To understand Unix, it is important to understand the ingredients of a process. In abstract terms, a 
process is a model of a computer in execution. See <a href=pdfs/lions.pdf>Lion's Chapter 7</a> or 
<a href=pdfs/unix_io_system.pdf>Thompson and Ritchies original Unix I/O paper</a> for better 
explanations than I can give. 

In concrete terms, a Unix v6 process consists of some memory (stack + heap + data segments + text), and 
some references to that memory (via a proc structure and a user structure). The proc structure contains
essential information pertaining to a process. Although the operating system only concerns itself with
one process at a time, the proc structures for each process are <b>never swapped out</b>. 

```c
/* Lines 0350 - 0376 in the source
 * The proc structure.
 * One allocated per active process.
 * Contains all data needed about the process
 * while the process may be swapped out
 * Other per process data (user.h)
 * is swapped with the process.
 */
struct proc
{
  char p_stat;
  char p_flag;
  char p_pri;    /* priority, negative is high */
  char p_sig;    /* signal number sent to this process */
  char p_uid;    /* user id, used to direct tty signals */
  char p_time;   /* resident time for scheduling */
  char p_cpu;    /* cpu usage for scheduling */
  char p_nice;   /* nice for scheduling */
  int  p_ttyp;   /* controlling tty */
  int  p_pid;    /* unique process id */
  int  p_ppid;   /* process id of parent */
  int  p_addr    /* addr of swappable image */
  int  p_size;   /* size of swappable image (*64 bytes) */
  int  p_wchan;  /* event process is awaiting */
  int  *p_textp; /* pointer to text structure */
} proc[NPROC];
```

The user structure is much larger, and contains important (but non-essential) information pertaining to
the process. As mentioned above, the operating system only concerns itself with one process at a time.
In real terms, what this means is that the operating system only works with one user structure at a time.
The "active" user structure is always found at virtual kernel address location 140000. This makes it easy
for the operating system to find and manipulate the user structure, and prevents potential complications that
could arise from more aggresive use of the MMU's addressing capabilities. 

```c
/* Lines 0400 - 0460 in the source
 * The user structure.
 * One allocated per process.
 * Contains all per process data
 * that doesn't need to be referenced
 * while the process is swapped
 * The user block is USIZE*64 bytes
 * long; resides at virtual kernel
 * loc 140000; contains the system
 * stack per user; is cross referenced
 * with theproc structure for the
 * same process
 */ 
struct user
{
  int u_rsav[2];
  int u_fsav[24];

  char u_segflg;
  char u_error;
  char u_uid;
  char u_gid;
  char u_ruid;
  char u_rgid;
  int u_procp;
  char *u_base;
  char *u_count;
  char *u_offset[2];
  int *u_cdir;
  char u_dbuf[DIRSIZ];
  char *u_dirp;
  struct {
    int u_ino;
    char u_name[DIRSIZ];
  } u_dent;
  int *u_pdir;
  int u_uisa[16];
  int u_uisd[16];
  int u_ofile[NOFILE];

  int u_arg[5];
  int u_tsize;
  int u_dsize;
  int u_ssize;
  int u_sep;
  int u_qsav[2];
  int u_ssav[2];
  int u_signal[NSIG];
  int u_utime;
  int s_utime;
  int u_cutime[2];
  int u_cstime[2];
  int *u_ar0;
  int u_prof[4];
  char u_intflg;

} u;
```
The operating system maintains a reference to the user structure through the seventh kernel segmentation address registers
(commonly referred to in the source as KISA6). <b> This is the only kernel segmentation address register that is manipulated
after startup </b>. All the other kernel segmentation registers are initialized in lines 0620 - 0630 and remain constant until
the machine shuts down. 

<h1> Enough talk - Show me the code </h1>

After initializing segmentation registers (0620 - 0645) and setting some data areas to zero (0645 - 0665), the OS source shows
a puzzling few lines of code:

```c
mov $30000, PS
jsr pc, _main
mov $170000, -(sp)
clr -(sp)
rtt
```

The first line manipulates the processor status word to indicate the previous mode as user mode and the current mode as kernel mode
(this will be important later). The second line then uses an instruction called JSR, which deserves some description. JSR has the 
following instruction format:

jsr <i>reg dest</i>

<ol>
<li> Push reg onto the stack </li>
<li> Save the current PC in reg </li>
<li> Set the PC to dest </li>
</ol>

In this case, the effect of JSR is that the current PC (which points to line 3) is pushed onto the stack, and the PC is set to 
_main (1550 in the source). But, as the commentary in Lions points out, the call on main() never returns. So why does the
code even have lines 3-5 in the first place? More on that later, but if you're curious now, check out ```bash man fork() ```.

main() starts by clearing higher areas of physical memory. The memory clearing leverages fuibyte() to determine the end of
physical memory. Each time a a memory block is found, it is initalized to zero and added to a list of free memory blocks
via a call on mfree(). 

After adding memory to the free list, main() allocates some space on the swap map so data can be swapped from main memory
to disk. See <a href=Malloc_and_Free.md>commentary on malloc and free</a> if you forgot how this works.

At this point, the OS is on line 1589, and is ready to start setting up the first process (proc[0]). The OS sets a few important
fields, then links the user structure to point to the new process.

```c
proc[0].p_addr = *ka6;
proc[0].p_size = USIZE;
proc[0].p_stat = SRUN;
proc[0].p_flag =| SLOAD|SSYS;
u.u_procp = &proc[0];
```

The OS then proceeds to set the machine's clock and initialize the file system. We'll skip those steps for now.
The OS finally reaches line 1627, and we've finally reached the point where we need to talk about the stack.

Each process in Unix v6 has a stack region. The stack is used to store variables, and helps to facilitate function
calls. The Unix stack grows down toward lower addresses, so the bottom of the stack actually has a higher
virtual address than the top of the stack.

Before the call to newproc() on line 1627, the stack looks (roughly) like this:
-----------
|r2       | <- sp
-----------
|r3       |
-----------
|r4       |
-----------
|r5 (=0)  | <- (=usize+64. - 2)
-----------
|pc (=670)|
-----------

This should surprise you. After all, the only explicit stack operation that we have seen up to this point is the
jsr <i> pc, _main </i> in line 0669. The JSR is responsible for pushing PC onto the stack, but how did r2 - r5
get there?

The answer: calling conventions. Calling conventions define how the operating system enters and exits functions.
In this case, the calling convention is

```c
.globl csv
csv:
  mov r5, r0
  mov sp, r5
  mov r4, -(sp)
  mov r3, -(sp)
  mov r2, -(sp)
  jsr pc, (r0)

.globl cret
cret:
  mov r5, r1
  mov -(r1), r4
  mov -(r1), r3
  mov -(r1), r2
  mov r5, sp
  mov (sp)+, r5
  rts pc
```

The C compiler references the calling convention by inserting the following line at the beginning of every C function
body:

```c
C-function:
  jsr r5, csv 
```

The key point to understand here is that we want to save registers r2 - r5 before entering a new function. If we 
save the registers on the stack, we can restore them later once the new function exits without losing context.

The r5 register in the PDP architecture is especially significant. r5 is often referred to as "the environment pointer".
Its job is to save the location of the prior environment pointer. Since csv is called from C-function (and r5 is at
the top of the stack as a result of the JSR in the C-function body), saving r5 is as simple as mov sp, r5. 

As an additional note: that jsr pc, (r0) at the end of csv isn't trying to save anything in particular - it's just trying
to make room on the stack. See <a href=https://pdos.csail.mit.edu/6.828/2005/lec/v6-calling.html> this digression on 
v6 calling conventions </a> for more info.

Getting back to stack visualization - once we reach newproc() (line 1827), the stack looks roughly like this
---------------------
|r2                 | <- sp
---------------------
|r3                 |
---------------------
|r4                 |
---------------------
|r5 (=usize+64. - 2)| <- r5
---------------------
|pc (=1627)         |
---------------------
|r2                 | <- sp
---------------------
|r3                 |
---------------------
|r4                 |
---------------------
|r5 (=0)            | <- r5 (=usize+64. - 2)
---------------------
|pc (=670)          |
---------------------

The first thing new proc does is find a unique process id (1840 - 1855). This pid serves to uniquely identify a process. 
As this is the first time newproc() is being called, the unique process id will be 1.

Newproc then sets up the process (1859 - 1870). This setup assumes the existence of a currently running process which can
be found at u.u_procp. As this is the first process, all that setup can be ignored (although we will circle back
to this when talking about subsequent processes).

More setup occurs (1870 - 1888), and then we reach a critical line - ```c savu(u.u_rsav);```. This line calls a special
function, savu, which does the following:

```c
_savu:
  bis $340, PS
  mov (sp)+, r1
  mov (sp), r0
  mov sp, (r0)+
  mov r5, (r0)+
  bic $340, PS
  jmp (r1)
```
The first line sets savu() to run at the highest priority (so it won't get interrupted). The second and third lines pop
the return address and argument into r1 and r0, respectively. 

The fourth and fifth lines are the most important. These lines save the current sp and r5 registers to the location 
specified by the argument to savu(). In this case, the registers end up getting stored in the u_rsav field of the
currently loaded user struct for the process. The fifth line sets the priority back down to zero, and the sixth
jumps back into newproc().

Why are these seven lines important?

Well, what happens when we want to context switch? There's a lot that goes on in a context switch, but, at its core,
two basic things happen:

  1. We save the state of the currently executing process to somewhere
  2. We restore the state of the process we'd like to switch to from somewhere

Savu() does step 1! If we capture the stack and environment pointers for the currently executing process, we can 
restore them later without a loss of context. Note that the restoration work is done by retu(), which will 
be discussed in more detail later on.

```c
_retu:
  bis $340, PS
  mov (sp)+, r1
  mov (sp), $KISA6
  mov $_u, r0
1:
  mov (r0)+, sp
  mov (r0)+, r5
  bic $340, PS
  jmp (r1)
```
Going back to newproc: lines 1890 - 1896 set up the new process. A call to malloc() in line 1896 allocates space for 
the process. If that malloc call is not successful, a couple of things happen:

  1. The process state is set to SIDL
  2. The process address is set to whatever p_addr the current process in the user struct has
  3. A call on savu is made once again, but this time with an argument of u.u_ssav
  4. xswap() is called, swapping out the new process before it even got a chance to run
  5. The process flag is set to SSWAP (indicating that it is swapped out), and its status is set to SRUN (indicating that it 
     wants to run)

On the other hand, if malloc() worked, newproc() can just:
  1. Set the p_addr of the new process to point to the newly allocated area
  2. Copy memory from the old process to the new process via copyseg()

Finally, newproc sets the user structure's u_procp field to point to the newly created process and returns a value of zero.

At this point, the call to newproc() on line 1627 resolves with a value of 0, so the conditional is not taken. Sched() is
subsequently called on line 1637.

Sched immediately goes to the loop label, where it looks for a process that wants to run ```c(rp->p_stat == SRUN)``` and is 
not loaded in core ```c((rp->p_flag&SLOAD)==0)```. Finding none (process #1 is loaded in core), sched increments runout and sleeps
on it with a priority of -100 (this is a very high priority, and the negative indicates that the process cannot be interrupted
from its sleep by signals).

Sleep sets some flags on the proc struct to indicate what variable the process is sleeping on (rp->p_wchan = chan;), that
the process is sleeping (rp->p_stat = SSLEEP;), and the priority of the sleep (rp->p_pri = pri;). Sleep then calls swtch()
for a context switch.

Swtch() begins by calling ```c savu(u.u_rsav);``` to save the context of the current process (we saw this before in newproc() line
1889, but the stack is significantly deeper this time, looking something like: main() -> sched() -> sleep() -> swtch()). Swtch()
then performs a context switch to process zero - but as the OS is already "in" process 0, this has no effect! Swtch() then loops
to find a process that wants to run (rp->p_stat == SRUN) and is loaded in core memory ((rp->p_flag & SLOAD) != 0). And process
#1 satisfies both of these conditions! Finding process #1, swtch() sets the current priority to process #1's priority and,
at long last, performs a context switch to process #1 via retu(rp->paddr); Swtch() then calls sureg() to set up segmentation registers
appropriate to process 1 (these were copied over as part of the call to copyseg() in newproc(), although I don't believe they changed
as a result of this copy)

There's a cryptic bit starting at line 2239 which deals with custom logic needed during swaps. Lions gives a good explanation as to why
these lines are neccessary. I'll defer writing my own explanation for now.

Finally, proc #1 returns from swtch() with a value of 1. <b>But to where?</b>

Believe it or not, proc #1 actually returns to line 1627 in main. How? Go back to that savu in newproc, line 1889.

```c savu(u.u_rsav);```

At the time, the stack looked like this:
---------------------
|r2                 | <- sp
---------------------
|r3                 |
---------------------
|r4                 |
---------------------
|r5 (=usize+64. - 2)| <- r5
---------------------
|pc (=1627)         |
---------------------
|r2                 | <- sp
---------------------
|r3                 |
---------------------
|r4                 |
---------------------
|r5 (=0)            | <- r5 (=usize+64. - 2)
---------------------
|pc (=670)          |
---------------------

The copyseg() on line 1915 copied the savu'd sp and r5 from proc #0's memory to proc #1's. So the retu on line 2228 restores the
saved sp and r5. So, when swtch() returns, it returns to the saved PC, which points to line 1627 in the source. And, as indicated,
the returned value is 1.

Because the returned value is 1, main() enters the conditional. The size of the data+stack region is expanded, and data from the original
data area is copied into this new area. Estabur sets the prototype segmentation registers and calls sureg to copy these into the hardware.

Finally, copyout copies the icode array from kernel space into user space (copying starts at location 0), and main() returns.

At this point, we have 3 instructions left to run

```c
mov $170000, -(sp)
clr -(sp)
rtt
```

The last three instructions set the processor to user mode, add an empty value to the top of the stack, and return. The rtt returns to address
zero, where icode is waiting to be executed...

Icode starts up the init process. In C, it would be roughly analogous to:

```c
char *init "/etc/init";
main()
{
    while(1) {
        execl(init, init, 0);
    }
}
```

And that's it. 

<h1> More to the story </h1>

Just joking. Obviously the UNIX OS does a lot more than exist. The Unix OS is responsible for a lot, lot more (otherwise it wouldn't have won a 
Turing award). Some of the other responsibilities the kernel has

<h1> Outstanding Remarks </h1>

You've probably noticed that I didn't give full explanations for all of the code in this section. In some cases (like malloc and free), that's 
because I've already written commentary elsewhere. In others (estabur and sureg), that's because I don't fully understand the code myself. 
If you're curious, <a href=pdfs/unix_v6.pdf>read the source</a>! 

<h1> Further Reading </h1>

Nothing's better than <a href=pdfs/unix_v6.pdf>the source</a>

In my opinion<a href=pdfs/lions.pdf>Lion's should be your first source for detailed Unix v6 questions</a>

<a href=https://gunkies.org>The Gunkies forum</a> has a bunch of good articles relating to the architecture of the PDP11. That info will be important if you wish to do an in-depth study of v6.

The <a href=pdfs/pdp11-40.pdf>PDP11 user manual</a> is a great source for PDP11 specific questions, especially ones relating to the instruction set. It's highly readable.

Russ Cox taught a course at MIT centered around <a href=https://pdos.csail.mit.edu/6.828/2005/lec/l5.html>Unix v6</a> (this later moved to xv6, which is a teaching implementation of unix v6 that might be of 
interest if you're looking to use MIT course materials extensively). There's a reason Russ was (is?) at MIT - he's brilliant. His commentary is sparse but of very high quality.

<a href=pdfs/the_design_of_the_unix_operating_system>The Design of the Unix Operating System</a> by Maurice Bach is a good textbook detailing the internals of the System V UNIX operating system
(closely related to unix v6). Bach centers his commentary around the algorithms that UNIX uses. His explanation has little code, but is fairly exhaustive. If you like more of a textbook 
approach to learning operating systems, this book might be for you.
