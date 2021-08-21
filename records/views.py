from django.db.models import Q
from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import DetailView, UpdateView, ListView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.detail import SingleObjectMixin
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin

from .choices import BE_PROGRAM_CHOICES, MSC_PROGRAM_CHOICES, PROGRAM_LEVEL_CHOICES, GROUPED_PROGRAM_CHOICES
from .models import Student
from .forms import LoginForm, AddressFormSet, AlumniForm, FurtherAcademicStatusFormSet, YearbookViewForm
from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.db import transaction

from django.core.exceptions import ValidationError

from allauth.account import views as allauth_accounts_views
from django.contrib.auth import logout
from django.contrib.auth.models import Group
from django.urls import reverse

be_programs_list = [program[0] for program in BE_PROGRAM_CHOICES]
msc_programs_list = [program[0] for program in MSC_PROGRAM_CHOICES]
phd_programs_list = ['PhD']


# Create your views here.
def record_home(request):
    context = {}
    # return render(request, 'records/base.html', context)
    if request.method == "POST":
        form = YearbookViewForm(data=request.POST)
        if form.is_valid():
            return redirect(
                'yearbook-view',
                batch_bs=form.data.get('batch_bs'),
                program_code=form.data.get('program'),
            )
        else:
            messages.warning(request, f'No records for given year and program')
    else:
        form = YearbookViewForm()
    context = {
        'form': form,
    }
    return render(request, 'records/home.html', context)


class YearbookListView(ListView):
    model = Student
    template_name = 'records/yearbook_list.html'
    context_object_name = 'students'

    def get_queryset(self):
        if self.kwargs['program_code'] in be_programs_list:
            try:
                bachelor = Student.objects.filter(
                    be_program__iexact=self.kwargs['program_code'],
                    be_batch_bs__iexact=self.kwargs['batch_bs'],
                ).order_by('be_roll_number')
                return bachelor
            except Student.DoesNotExist:
                raise Http404("No Alumni matches the given query.")
        elif self.kwargs['program_code'] in msc_programs_list:
            try:
                master = Student.objects.filter(
                    msc_program__iexact=self.kwargs['program_code'],
                    msc_batch_bs__iexact=self.kwargs['batch_bs'],
                ).order_by('msc_roll_number')
                return master
            except Student.DoesNotExist:
                raise Http404("No Alumni matches the given query.")
        elif self.kwargs['program_code'] in phd_programs_list:
            try:
                phd = Student.objects.filter(
                    phd_batch_bs__iexact=self.kwargs['batch_bs'],
                ).order_by('phd_roll_number')
                return phd
            except Student.DoesNotExist:
                raise Http404("No Alumni matches the given query.")
        else:
            raise Http404("No Alumni matches the given query.")


def alumni_login(request):
    #added in 2075 #does this have any side effects? just using this as it seems to work... for now 
    #if a logged in user comes back to this page then if logged in hellore below gives an error...
    #if request.user.is_authenticated:
    logout(request)

    form = LoginForm()
    
    if request.method == "POST":
        if 'roll_number' in request.POST:
            form = LoginForm(data=request.POST)
            if form.is_valid():
                kwargs={
                    'last_name':form.data.get('last_name'),
                    'batch_bs':form.data.get('batch_bs'),
                    'program_code':form.data.get('program'),
                    'roll_number':form.data.get('roll_number')
                }
                studnt = get_student_object(kwargs,Student.objects.filter(),form.data.get('dob_bs'))
                if studnt.user_account is not None:
                    messages.warning(request, f'You need to login with your email and password.')# {studnt.first_name}.')
                    return redirect(reverse('alumni-login')) 
                return redirect(
                    'record-update',
                    batch_bs=form.data.get('batch_bs'),
                    program_code=form.data.get('program'),
                    roll_number=form.data.get('roll_number'),
                    last_name=form.data.get('last_name').strip(), #i know this is bad form but its past midnight and I am tired af. Sorry :D
                    dob_bs=form.data.get('dob_bs').replace('/', ''),
                )
            else:
                messages.warning(request, f'Record not found! Please check credentials properly')
        else:
            #return HttpResponse("ynha aayo...")
            allauth_accounts_views.login(request)
            if request.user.is_authenticated:
                return allauth_accounts_views.login(request)
            pass
    
    #return HttpResponse("ynha aayo... ta")#delete this line
    # else:
    #     form = LoginForm()
    context = {
        'form': form,
        'hellore':allauth_accounts_views.login(request).render().content.decode('utf-8')
    }
    return render(request, 'records/alumni_login.html', context)

#added in 2075
def alumni_logged_in(request):
    if not request.user.is_authenticated:
        return redirect(reverse('alumni-login'))
    elif not request.user.groups.filter(name="Students").exists():
        return redirect(reverse('alumni-login'))
    
    studnt = request.user.student_user
    params = [ ]

    be_programs_list = [program[0] for program in BE_PROGRAM_CHOICES]
    msc_programs_list = [program[0] for program in MSC_PROGRAM_CHOICES]
    phd_programs_list = ['PhD']

    if studnt.be_program is not None :
        #messages.info(request,f"be program {studnt.be_program} in {be_programs_list}")
        if studnt.be_program in be_programs_list:
            params = [
                studnt.be_batch_bs, studnt.be_program, studnt.be_roll_number,studnt.last_name,studnt.dob_bs
            ]
    elif studnt.msc_program is not None :
        if studnt.msc_program in msc_programs_list:
            params = [
                studnt.msc_batch_bs, studnt.msc_program, studnt.msc_roll_number,studnt.last_name,studnt.dob_bs
            ]
    elif studnt.phd_batch_bs is not None:
        params = [
            studnt.phd_batch_bs, studnt.phd_roll_number,studnt.last_name,studnt.dob_bs
        ]
    else:
        messages.warning(request, f'No student with given credentials was found')
        return redirect(reverse('alumni-login'))
    
    if params[4] is not None:
        params[4]=params[4].replace('/','')
    else:
        params[4]=' '
    return redirect(
                'record-update-gate',
                batch_bs=params[0],
                program_code=params[1],
                roll_number=params[2],
                last_name=params[3],    #.strip(), ###i know this is bad form but its past midnight and I am tired af. Sorry :D
                dob_bs=params[4],
            )
    return HttpResponse("logged in haina ta...")

# the following is not used upto now
# we initially planned on showing a detail view of the Alumni,
# however, could not do so due to time constraints as well as not knowing what data to be shown
class AlumniDetailView(DetailView):
    model = Student
    queryset = Student.objects.filter()
    template_name = 'records/alumni_detail.html'

    # def get_context_data(self, **kwargs):
    #     context = super(EmployerDetailView, self).get_context_data(**kwargs)
    #     context['employer'] = self.object
    #     context['vacancies'] = self.object.vacancy_set.all().order_by('-deadline_date')
    #     return context

    def get_context_data(self, **kwargs):
        context = super(AlumniDetailView, self).get_context_data(**kwargs)
        context['alumni'] = self.object
        context['addresses'] = self.object.address_set.all()
        context['further_academic_status'] = self.object.academicstatus_set.all()
        return context

    def get_object(self, queryset=None):
        if self.kwargs['program_code'] in be_programs_list:
            try:
                bachelor = self.queryset.get(
                    last_name__iexact=self.kwargs['last_name'],
                    be_program__iexact=self.kwargs['program_code'],
                    be_batch_bs__iexact=self.kwargs['batch_bs'],
                    be_roll_number__iexact=self.kwargs['roll_number'],
                )
                return bachelor
            except Student.DoesNotExist:
                raise Http404("No Alumni matches the given query.")
        elif self.kwargs['program_code'] in msc_programs_list:
            try:
                master = self.queryset.get(
                    last_name__iexact=self.kwargs['last_name'],  
                    msc_program__iexact=self.kwargs['program_code'],
                    msc_batch_bs__iexact=self.kwargs['batch_bs'],
                    msc_roll_number__iexact=self.kwargs['roll_number'],
                )
                return master
            except Student.DoesNotExist:
                raise Http404("No Alumni matches the given query.")
        elif self.kwargs['program_code'] in phd_programs_list:
            try:
                phd = self.queryset.get(
                    last_name__iexact=self.kwargs['last_name'], 
                    phd_batch_bs__iexact=self.kwargs['batch_bs'],
                    phd_roll_number__iexact=self.kwargs['roll_number'],
                )
                return phd
            except Student.DoesNotExist:
                raise Http404("No Alumni matches the given query.")
        else:
            raise Http404("No Alumni matches the given query.")

def AlumniUpdateViewGate(request,batch_bs,program_code,roll_number,last_name,dob_bs):
    if not request.user.is_authenticated:
        messages.add_message(request,messages.WARNING,"You need to log in")
        return redirect(reverse('alumni-login'))
    if request.user.groups.filter(name="Students").exists():
        #a little bit inefficient?
        kwargs={
            'last_name':form.data.get('last_name'),
            'batch_bs':form.data.get('batch_bs'),
            'program_code':form.data.get('program'),
            'roll_number':form.data.get('roll_number')
        }
        studnt = get_student_object(kwargs,Student.objects.filter(),form.data.get('dob_bs'))
        if not studnt == request.user.student_user:
            return HttpResponse('Unauthorized', status=401)
    elif request.user.groups.filter(name="Institutes").exists():
        return AlumniUpdateView.as_view()(request,batch_bs=batch_bs,program_code=program_code,
                                          roll_number=roll_number,last_name=last_name,dob_bs=dob_bs,app_name="institutuff")
        pass
    else: 
        return HttpResponse('Unauthorized Group...', status=401)
    return AlumniUpdateView.as_view()(request,batch_bs=batch_bs,program_code=program_code,
                                      roll_number=roll_number,last_name=last_name,dob_bs=dob_bs,app_name="records")

class AlumniUpdateView(SuccessMessageMixin, UpdateView):
    model = Student
    template_name = '/alumni_form.html'
    queryset = Student.objects.filter()
    form_class = AlumniForm
    success_message ="Alumni record updated successfully!"


    def get_context_data(self, **kwargs):
        data = super(AlumniUpdateView, self).get_context_data(**kwargs)
        if self.request.POST:
            data['addresses'] = AddressFormSet(self.request.POST, instance=self.object)
            data['furtheracademicstatus'] = FurtherAcademicStatusFormSet(self.request.POST, instance=self.object)
        else:
            self.template_name = self.kwargs['app_name'] + '/alumni_form.html'
            data['addresses'] = AddressFormSet(instance=self.object)
            data['furtheracademicstatus'] = FurtherAcademicStatusFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        addresses = context['addresses']
        further_academic_status = context['furtheracademicstatus']
        with transaction.atomic():
            form.instance.created_by = self.request.user###???
            self.object = form.save()
            if addresses.is_valid():
                addresses.instance = self.object
                addresses.save()
            else:
                messages.warning(self.request, f'Address invalid')
                return super(AlumniUpdateView, self).form_invalid(form)
            if further_academic_status.is_valid():
                further_academic_status.instance = self.object
                further_academic_status.save()
            else:
                messages.warning(self.request, f'Further Academic status invalid')
                return super(AlumniUpdateView, self).form_invalid(form)
        return super(AlumniUpdateView, self).form_valid(form)

    def get_object(self, queryset=None):
        #raise ValidationError(self.kwargs) just for debug message...
        return get_student_object(self.kwargs,self.queryset,self.kwargs['dob_bs'])

    def get_form(self, *args, **kwargs):
        dob_bs = self.kwargs['dob_bs']
        dob_bs = dob_bs[:4]+'/'+dob_bs[4:6]+'/'+dob_bs[6:] if len(dob_bs)>4 else dob_bs
        form = super(AlumniUpdateView, self).get_form(*args, **kwargs)
        if not form.base_fields['dob_bs']:
            form.base_fields['dob_bs']= dob_bs
        return form

    def get_initial(self):
        dob_bs = self.kwargs['dob_bs']
        dob_bs = dob_bs[:4]+'/'+dob_bs[4:6]+'/'+dob_bs[6:] if len(dob_bs)>4 else dob_bs
        return {
            'dob_bs': dob_bs,
        }

def get_student_object(kwargs,queryset=None, dob_bs=None):
    #dob_bs = self.kwargs['dob_bs']
    if dob_bs is not None:
        dob_bs = dob_bs[:4]+'/'+dob_bs[4:6]+'/'+dob_bs[6:]
    ret_object=None
    if kwargs['program_code'] in be_programs_list:
        try:
            bachelor = queryset.get(Q(
                last_name__iexact=kwargs['last_name'], 
                be_program__iexact=kwargs['program_code'],
                be_batch_bs__iexact=kwargs['batch_bs'],
                be_roll_number__iexact=kwargs['roll_number'],
                dob_bs__exact=dob_bs,
            ) | Q(
                last_name__iexact=kwargs['last_name'],
                be_program__iexact=kwargs['program_code'],
                be_batch_bs__iexact=kwargs['batch_bs'],
                be_roll_number__iexact=kwargs['roll_number'],
                dob_bs__isnull=True,
            ))
            ret_object = bachelor
            #return bachelor
        except Student.DoesNotExist:
            raise Http404(f"No Alumni matches the given query {kwargs['last_name']} {kwargs['program_code']} {kwargs['batch_bs']} .")
    elif kwargs['program_code'] in msc_programs_list:
        try:
            master = queryset.get( Q(
                last_name__iexact=kwargs['last_name'], 
                msc_program__iexact=kwargs['program_code'],
                msc_batch_bs__iexact=kwargs['batch_bs'],
                msc_roll_number__iexact=kwargs['roll_number'],
                dob_bs__exact=dob_bs,
            ) | Q(
                last_name__iexact=kwargs['last_name'],
                msc_program__iexact=kwargs['program_code'],
                msc_batch_bs__iexact=kwargs['batch_bs'],
                msc_roll_number__iexact=kwargs['roll_number'],
                dob_bs__isnull=True,
            ))
            ret_object = master
        except Student.DoesNotExist:
            raise Http404("No Alumni matches the given query.")
    elif kwargs['program_code'] in phd_programs_list:
        try:
            phd = queryset.get( Q(
                last_name__iexact=kwargs['last_name'], 
                phd_batch_bs__iexact=kwargs['batch_bs'],
                phd_roll_number__iexact=kwargs['roll_number'],
                dob_bs__exact=dob_bs,
            ) | Q(
                last_name__iexact=kwargs['last_name'],
                phd_batch_bs__iexact=kwargs['batch_bs'],
                phd_roll_number__iexact=kwargs['roll_number'],
                dob_bs__isnull=True,
            ))
            ret_object = phd
        except Student.DoesNotExist:
            raise Http404("No Alumni matches the given query.")
        # if self.get_object().username is not None:
        #     messages.warning(request, f'You need to login with your email and password.')
        #     return redirect(reverse('alumni-login')) 
    else:
        raise Http404("No Alumni matches the given query.")
    return ret_object
